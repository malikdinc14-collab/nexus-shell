//! Daemon server — two Unix socket listeners, JSON-RPC 2.0, all through dispatch().

use crate::event_bridge::{EventConnection, SharedConnections, SubscriptionFilter};
use nexus_client::{JsonRpcRequest, JsonRpcResponse};
use nexus_engine::NexusCore;
use std::collections::HashMap;
use std::sync::{Arc, Mutex as StdMutex};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixListener;
use tokio::sync::watch;

/// Shared engine state (std::sync::Mutex, NOT tokio).
pub type SharedCore = Arc<StdMutex<NexusCore>>;

/// Connected client counter for idle shutdown.
pub type ClientCount = Arc<std::sync::atomic::AtomicUsize>;

/// Run the command socket accept loop.
pub async fn run_command_listener(
    listener: UnixListener,
    core: SharedCore,
    client_count: ClientCount,
    mut shutdown: watch::Receiver<bool>,
) {
    loop {
        tokio::select! {
            result = listener.accept() => {
                match result {
                    Ok((stream, _)) => {
                        client_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        let core = core.clone();
                        let count = client_count.clone();
                        tokio::spawn(async move {
                            handle_command_connection(stream, core).await;
                            count.fetch_sub(1, std::sync::atomic::Ordering::Relaxed);
                        });
                    }
                    Err(e) => eprintln!("command accept error: {e}"),
                }
            }
            _ = shutdown.changed() => {
                break;
            }
        }
    }
}

/// Run the event socket accept loop.
pub async fn run_event_listener(
    listener: UnixListener,
    connections: SharedConnections,
    mut shutdown: watch::Receiver<bool>,
) {
    loop {
        tokio::select! {
            result = listener.accept() => {
                match result {
                    Ok((stream, _)) => {
                        let conns = connections.clone();
                        tokio::spawn(async move {
                            handle_event_connection(stream, conns).await;
                        });
                    }
                    Err(e) => eprintln!("event accept error: {e}"),
                }
            }
            _ = shutdown.changed() => {
                break;
            }
        }
    }
}

async fn handle_command_connection(
    stream: tokio::net::UnixStream,
    core: SharedCore,
) {
    let (reader, mut writer) = stream.into_split();
    let mut lines = BufReader::new(reader).lines();

    while let Ok(Some(line)) = lines.next_line().await {
        let response = match serde_json::from_str::<JsonRpcRequest>(&line) {
            Ok(req) => {
                let core = core.clone();
                let method = req.method.clone();
                let params = req.params.clone();
                let id = req.id;

                // Convert params Value to HashMap for dispatch
                let args: HashMap<String, serde_json::Value> = match &params {
                    serde_json::Value::Object(map) => {
                        map.iter().map(|(k, v)| (k.clone(), v.clone())).collect()
                    }
                    _ => HashMap::new(),
                };

                // spawn_blocking to avoid blocking tokio runtime
                match tokio::task::spawn_blocking(move || {
                    let mut core = core.lock().unwrap();
                    nexus_engine::dispatch(&mut core, &method, &args)
                }).await {
                    Ok(Ok(result)) => JsonRpcResponse::success(id, result),
                    Ok(Err(e)) => JsonRpcResponse::error(id, -1, &e.to_string()),
                    Err(e) => JsonRpcResponse::error(id, -2, &format!("internal: {e}")),
                }
            }
            Err(e) => JsonRpcResponse::error(0, -32700, &format!("parse error: {e}")),
        };

        let mut out = match serde_json::to_string(&response) {
            Ok(s) => s,
            Err(_) => r#"{"jsonrpc":"2.0","id":0,"error":{"code":-32603,"message":"serialize failed"}}"#.into(),
        };
        out.push('\n');

        if writer.write_all(out.as_bytes()).await.is_err() {
            break;
        }
    }
}

async fn handle_event_connection(
    stream: tokio::net::UnixStream,
    connections: SharedConnections,
) {
    let (reader, writer) = stream.into_split();
    let mut lines = BufReader::new(reader).lines();

    // Read subscribe requests
    while let Ok(Some(line)) = lines.next_line().await {
        let req: JsonRpcRequest = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(_) => continue,
        };

        if req.method != "subscribe" {
            continue;
        }

        let patterns: Vec<String> = req.params.get("patterns")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();

        let filter: HashMap<String, serde_json::Value> = req.params.get("filter")
            .and_then(|v| v.as_object())
            .map(|m| m.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
            .unwrap_or_default();

        // Build ack
        let ack = JsonRpcResponse::success(req.id, serde_json::json!({
            "patterns": patterns,
            "filter": filter,
        }));
        let mut ack_line = serde_json::to_string(&ack).unwrap_or_default();
        ack_line.push('\n');

        let conn = EventConnection {
            writer,
            sub: SubscriptionFilter { patterns, filter },
        };

        // Register connection and write ack through its writer
        let mut conns = connections.lock().await;
        conns.push(conn);
        let last = conns.last_mut().unwrap();
        let _ = last.writer.write_all(ack_line.as_bytes()).await;
        drop(conns);

        // v1 LIMITATION: writer is moved into EventConnection on first subscribe.
        // Resubscription requires client to disconnect and reconnect.
        break;
    }
}

/// Check idle conditions and trigger shutdown if idle for 30s.
pub async fn idle_shutdown_monitor(
    core: SharedCore,
    client_count: ClientCount,
    shutdown_tx: watch::Sender<bool>,
) {
    let mut idle_seconds = 0u32;

    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;

        let clients = client_count.load(std::sync::atomic::Ordering::Relaxed);
        let ptys = {
            let core = core.lock().unwrap();
            core.active_pty_count()
        };

        if clients == 0 && ptys == 0 {
            idle_seconds += 5;
            if idle_seconds >= 30 {
                eprintln!("Idle for 30s with no clients and no PTYs — shutting down");
                let _ = shutdown_tx.send(true);
                return;
            }
        } else {
            idle_seconds = 0;
        }
    }
}
