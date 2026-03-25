//! Unix socket server — accepts connections, routes commands to NexusCore.

use crate::protocol::{Request, Response};
use nexus_engine::{Direction, Nav, NexusCore, PaneType};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixListener;
use tokio::sync::Mutex;

pub use nexus_core::constants::socket_path;

/// Shared engine state.
pub type SharedCore = Arc<Mutex<NexusCore>>;

/// Start the daemon server. Runs until cancelled.
pub async fn run(listener: UnixListener, core: SharedCore) {
    loop {
        match listener.accept().await {
            Ok((stream, _addr)) => {
                let core = core.clone();
                tokio::spawn(async move {
                    handle_connection(stream, core).await;
                });
            }
            Err(e) => {
                eprintln!("accept error: {e}");
            }
        }
    }
}

async fn handle_connection(stream: tokio::net::UnixStream, core: SharedCore) {
    let (reader, mut writer) = stream.into_split();
    let mut lines = BufReader::new(reader).lines();

    while let Ok(Some(line)) = lines.next_line().await {
        let response = match serde_json::from_str::<Request>(&line) {
            Ok(req) => dispatch(req, &core).await,
            Err(e) => Response::err(&format!("parse error: {e}")),
        };

        let mut out = serde_json::to_string(&response).unwrap_or_else(|_| {
            r#"{"status":"error","error":"serialize failed"}"#.into()
        });
        out.push('\n');

        if writer.write_all(out.as_bytes()).await.is_err() {
            break;
        }
    }
}

async fn dispatch(req: Request, core: &SharedCore) -> Response {
    let mut core = core.lock().await;

    match req.cmd.as_str() {
        // -- Session --
        "session.create" => {
            let name = str_arg(&req.args, "name").unwrap_or("nexus".into());
            let cwd = str_arg(&req.args, "cwd").unwrap_or_else(|| {
                std::env::current_dir()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_else(|_| "/tmp".into())
            });
            let session = core.create_workspace(&name, &cwd);
            Response::ok(serde_json::json!({ "session": session }))
        }
        "session.info" => {
            let session = core.session().map(|s| s.to_string());
            Response::ok(serde_json::json!({ "session": session }))
        }

        // -- Stack --
        cmd if cmd.starts_with("stack.") => {
            let op = &cmd[6..]; // strip "stack."
            let payload = string_payload(&req.args);
            let result = core.handle_stack_op(op, &payload);
            let mut data = serde_json::Map::new();
            data.insert("status".into(), serde_json::Value::String(result.status.clone()));
            for (k, v) in &result.data {
                data.insert(k.clone(), v.clone());
            }
            if result.status == "error" {
                Response::err(
                    result.data.get("error")
                        .and_then(|v| v.as_str())
                        .unwrap_or("stack operation failed"),
                )
            } else {
                Response::ok(serde_json::Value::Object(data))
            }
        }

        // -- Layout --
        "layout.show" => {
            Response::ok(core.layout.to_json())
        }
        "layout.split" => {
            let dir = match str_arg(&req.args, "direction").as_deref() {
                Some("horizontal" | "h") => Direction::Horizontal,
                _ => Direction::Vertical,
            };
            let pt = PaneType::from_str(
                &str_arg(&req.args, "pane_type").unwrap_or_else(|| "terminal".into()),
            );
            let new_id = core.layout.split_focused(dir, pt);
            Response::ok(serde_json::json!({
                "new_pane": new_id,
                "layout": core.layout.to_json(),
            }))
        }
        "layout.navigate" => {
            let nav = match str_arg(&req.args, "direction").as_deref() {
                Some("left" | "h") => Nav::Left,
                Some("down" | "j") => Nav::Down,
                Some("up" | "k") => Nav::Up,
                _ => Nav::Right,
            };
            core.layout.navigate(nav);
            Response::ok(serde_json::json!({
                "focused": core.layout.focused,
                "layout": core.layout.to_json(),
            }))
        }
        "layout.focus" => {
            let pane_id = str_arg(&req.args, "pane_id").unwrap_or_default();
            core.layout.set_focus(&pane_id);
            Response::ok(core.layout.to_json())
        }
        "layout.zoom" => {
            core.layout.toggle_zoom();
            Response::ok(serde_json::json!({
                "zoomed": core.layout.zoomed,
                "layout": core.layout.to_json(),
            }))
        }
        "layout.close" => {
            let pane_id = str_arg(&req.args, "pane_id").unwrap_or_default();
            core.layout.close_pane(&pane_id);
            Response::ok(core.layout.to_json())
        }
        "layout.resize" => {
            let pane_id = str_arg(&req.args, "pane_id").unwrap_or_default();
            let ratio = req.args.get("ratio")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.5);
            core.layout.set_ratio(&pane_id, ratio);
            Response::ok(core.layout.to_json())
        }

        _ => Response::err(&format!("unknown command: {}", req.cmd)),
    }
}

/// Extract a string arg from the JSON args map.
fn str_arg(args: &HashMap<String, serde_json::Value>, key: &str) -> Option<String> {
    args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
}

/// Convert JSON args to HashMap<String, String> for stack ops.
fn string_payload(args: &HashMap<String, serde_json::Value>) -> HashMap<String, String> {
    args.iter()
        .filter_map(|(k, v)| {
            v.as_str().map(|s| (k.clone(), s.to_string()))
        })
        .collect()
}
