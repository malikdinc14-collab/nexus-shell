//! Command dispatch — single domain.action entry point for all surfaces.
//!
//! Every surface (CLI, Tauri IPC, daemon socket, tmux keybinds) routes commands
//! through `dispatch()`. Commands take the form `"domain.action"`, e.g.
//! `"navigate.left"`, `"pane.split"`, `"stack.push"`.

use std::collections::HashMap;

use nexus_core::NexusError;
use nexus_core::surface::{SurfaceCapabilities, SurfaceMode, SurfaceRegistration};

use crate::core::NexusCore;
use crate::layout::{Direction, Nav};
use crate::persistence;

/// Route a `domain.action` command to the appropriate engine operation.
///
/// # Arguments
/// - `core`    — mutable engine reference
/// - `command` — `"domain.action"` string
/// - `args`    — arbitrary key/value parameters for the action
///
/// # Returns
/// JSON value on success, `NexusError` on failure.
pub fn dispatch(
    core: &mut NexusCore,
    command: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let (domain, action) = command
        .split_once('.')
        .ok_or_else(|| NexusError::InvalidState("command must be domain.action".into()))?;

    match domain {
        "navigate" => handle_navigate(core, action),
        "pane" => handle_pane(core, action, args),
        "stack" => handle_stack(core, action, args),
        "chat" => handle_chat(core, action, args),
        "pty" => handle_pty(core, action, args),
        "session" => handle_session(core, action, args),
        "keymap" => handle_keymap(core, action),
        "commands" => handle_commands(core, action),
        "layout" => handle_layout(core, action, args),
        "capabilities" => handle_capabilities(core, action, args),
        "nexus" => handle_nexus(action),
        "fs" => handle_fs(action, args),
        "editor" => handle_editor(core, action, args),
        "surface" => handle_surface(core, action, args),
        _ => Err(NexusError::NotFound(format!("unknown domain: {domain}"))),
    }
}

// ---------------------------------------------------------------------------
// navigate.*
// ---------------------------------------------------------------------------

fn handle_navigate(
    core: &mut NexusCore,
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    let nav = match action {
        "left" => Nav::Left,
        "right" => Nav::Right,
        "up" => Nav::Up,
        "down" => Nav::Down,
        _ => {
            return Err(NexusError::NotFound(format!(
                "unknown navigate action: {action}"
            )))
        }
    };

    core.layout.navigate(nav);
    core.mark_dirty();
    Ok(core.layout.to_json())
}

// ---------------------------------------------------------------------------
// pane.*
// ---------------------------------------------------------------------------

fn handle_pane(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    // Helper: extract a string arg.
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        // -- list ------------------------------------------------------------
        "list" => Ok(core.layout.pane_list()),

        // -- split variants --------------------------------------------------
        "split" | "split.vertical" | "split.horizontal" => {
            let direction = if action == "split.horizontal" {
                Direction::Horizontal
            } else if action == "split.vertical" {
                Direction::Vertical
            } else {
                // Fall back to args["direction"]
                match str_arg("direction").as_deref() {
                    Some("horizontal") => Direction::Horizontal,
                    _ => Direction::Vertical,
                }
            };

            let new_id = core.layout.split_focused(direction);
            core.mark_dirty();
            Ok(serde_json::json!({ "pane_id": new_id }))
        }

        // -- close -----------------------------------------------------------
        "close" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());

            if core.layout.close_pane(&pane_id) {
                core.mark_dirty();
                Ok(serde_json::json!({ "closed": pane_id }))
            } else {
                Err(NexusError::InvalidState(format!(
                    "cannot close pane: {pane_id}"
                )))
            }
        }

        // -- zoom ------------------------------------------------------------
        "zoom" => {
            core.layout.toggle_zoom();
            core.mark_dirty();
            Ok(core.layout.to_json())
        }

        // -- minimize --------------------------------------------------------
        "minimize" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            if core.layout.minimize_pane(&pane_id) {
                core.mark_dirty();
                Ok(serde_json::json!({ "minimized": pane_id }))
            } else {
                Err(NexusError::InvalidState(format!(
                    "cannot minimize pane: {pane_id}"
                )))
            }
        }

        // -- focus -----------------------------------------------------------
        "focus" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pane.focus requires pane_id arg".into())
            })?;

            if core.layout.set_focus(&pane_id) {
                core.mark_dirty();
                Ok(core.layout.to_json())
            } else {
                Err(NexusError::NotFound(format!("pane not found: {pane_id}")))
            }
        }

        // -- resize ----------------------------------------------------------
        "resize" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pane.resize requires pane_id arg".into())
            })?;

            let ratio = args
                .get("ratio")
                .and_then(|v| v.as_f64())
                .ok_or_else(|| {
                    NexusError::InvalidState("pane.resize requires numeric ratio arg".into())
                })?;

            if core.layout.set_ratio(&pane_id, ratio) {
                core.mark_dirty();
                Ok(core.layout.to_json())
            } else {
                Err(NexusError::NotFound(format!("pane not found: {pane_id}")))
            }
        }

        // -- pane.new.* ------------------------------------------------------
        // Split + push a tab with the requested role into the new pane's stack.
        _ if action.starts_with("new.") => {
            let role = action.strip_prefix("new.").unwrap_or("terminal");
            let new_id = core.layout.split_focused(Direction::Vertical);
            // Push an initial tab with the requested role into the new pane's stack
            let tab_name = {
                let mut c = role.chars();
                match c.next() {
                    None => String::new(),
                    Some(f) => f.to_uppercase().to_string() + c.as_str(),
                }
            };
            let mut tab = crate::stack::Tab::new(&tab_name);
            tab.role = Some(role.to_string());
            let (stack_id, _) = core.stacks.get_or_create_by_identity(&new_id, None);
            core.stacks.push(&stack_id, tab);
            core.mark_dirty();
            Ok(serde_json::json!({ "pane_id": new_id }))
        }

        _ => Err(NexusError::NotFound(format!("unknown pane action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// stack.*
// ---------------------------------------------------------------------------

fn handle_stack(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    // Convert serde_json::Value args to HashMap<String, String> for handle_stack_op.
    let string_args: HashMap<String, String> = args
        .iter()
        .filter_map(|(k, v)| {
            let s = match v {
                serde_json::Value::String(s) => s.clone(),
                serde_json::Value::Number(n) => n.to_string(),
                serde_json::Value::Bool(b) => b.to_string(),
                _ => return None,
            };
            Some((k.clone(), s))
        })
        .collect();

    let result = core.handle_stack_op(action, &string_args);

    if result.status == "ok" {
        core.mark_dirty();
    }

    let mut out = serde_json::json!({ "status": result.status });
    for (k, v) in result.data {
        out[k] = v;
    }
    Ok(out)
}

// ---------------------------------------------------------------------------
// chat.*
// ---------------------------------------------------------------------------

fn handle_chat(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "send" => {
            let pane_id = args.get("pane_id").and_then(|v| v.as_str()).ok_or_else(|| {
                NexusError::InvalidState("chat.send requires pane_id".into())
            })?;
            let message = args.get("message").and_then(|v| v.as_str()).ok_or_else(|| {
                NexusError::InvalidState("chat.send requires message".into())
            })?;
            let cwd = args.get("cwd").and_then(|v| v.as_str()).unwrap_or("/tmp");
            core.chat_send(pane_id, message, cwd)
                .map_err(NexusError::InvalidState)?;
            Ok(serde_json::Value::Null)
        }
        _ => Err(NexusError::NotFound(format!("unknown chat action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// pty.*
// ---------------------------------------------------------------------------

fn handle_pty(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    use nexus_core::surface::SurfaceMode;

    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    // In Delegated mode, the Mux backend owns PTY processes (e.g. tmux).
    // Forward spawn/write/kill to the Mux instead of PtyManager.
    if core.surfaces.active_mode() == SurfaceMode::Delegated {
        let pane_id = str_arg("pane_id").unwrap_or_default();
        return match action {
            "spawn" => {
                let _cwd = str_arg("cwd");
                let program = str_arg("program");
                let command = program.unwrap_or_else(|| "".to_string());
                if !command.is_empty() {
                    core.mux.attach_process(&pane_id, &command);
                }
                // For delegated surfaces, the mux already created the shell on split.
                Ok(serde_json::Value::Null)
            }
            "write" => {
                let data = str_arg("data").unwrap_or_default();
                core.mux.send_input(&pane_id, &data);
                Ok(serde_json::Value::Null)
            }
            "resize" => {
                let cols = args.get("cols").and_then(|v| v.as_u64()).unwrap_or(80) as u32;
                let rows = args.get("rows").and_then(|v| v.as_u64()).unwrap_or(24) as u32;
                use crate::surface::Dimensions;
                core.mux.resize(&pane_id, Dimensions { width: cols, height: rows });
                Ok(serde_json::Value::Null)
            }
            "kill" => {
                core.mux.destroy_container(&pane_id);
                core.mark_dirty();
                Ok(serde_json::Value::Null)
            }
            _ => Err(NexusError::NotFound(format!("unknown pty action: {action}"))),
        };
    }

    // Internal / Headless mode: engine's PtyManager owns PTY processes.
    match action {
        "spawn" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.spawn requires pane_id".into())
            })?;
            let cwd = str_arg("cwd");
            let program = str_arg("program");
            let prog_args: Option<Vec<String>> = args.get("args")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect());

            if let (Some(prog), Some(pargs)) = (program, prog_args) {
                core.pty_spawn_cmd(&pane_id, cwd.as_deref().unwrap_or("/tmp"), &prog, &pargs)
                    .map_err(NexusError::InvalidState)?;
            } else {
                core.pty_spawn(&pane_id, cwd.as_deref())
                    .map_err(NexusError::InvalidState)?;
            }
            core.mark_dirty();
            Ok(serde_json::Value::Null)
        }
        "write" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.write requires pane_id".into())
            })?;
            let data_b64 = str_arg("data").ok_or_else(|| {
                NexusError::InvalidState("pty.write requires data".into())
            })?;
            // Decode base64 wire encoding back to raw bytes
            use base64::Engine;
            let bytes = base64::engine::general_purpose::STANDARD.decode(&data_b64)
                .map_err(|e| NexusError::InvalidState(format!("base64 decode: {e}")))?;
            let decoded = String::from_utf8_lossy(&bytes);
            core.pty_write(&pane_id, &decoded)
                .map_err(NexusError::InvalidState)?;
            Ok(serde_json::Value::Null)
        }
        "resize" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.resize requires pane_id".into())
            })?;
            let cols = args.get("cols").and_then(|v| v.as_u64()).unwrap_or(80) as u16;
            let rows = args.get("rows").and_then(|v| v.as_u64()).unwrap_or(24) as u16;
            core.pty_resize(&pane_id, cols, rows)
                .map_err(NexusError::InvalidState)?;
            Ok(serde_json::Value::Null)
        }
        "kill" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.kill requires pane_id".into())
            })?;
            core.pty_kill(&pane_id)
                .map_err(NexusError::InvalidState)?;
            core.mark_dirty();
            Ok(serde_json::Value::Null)
        }
        _ => Err(NexusError::NotFound(format!("unknown pty action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// session.*
// ---------------------------------------------------------------------------

fn resolve_nexus_home(args: &HashMap<String, serde_json::Value>) -> std::path::PathBuf {
    if let Some(path) = args.get("_nexus_home").and_then(|v| v.as_str()) {
        return std::path::PathBuf::from(path);
    }
    persistence::nexus_home()
}

fn handle_session(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    let ws_name = core.session().unwrap_or("unnamed").to_string();

    match action {
        "create" => {
            let name = str_arg("name").unwrap_or_else(|| "nexus".to_string());
            let cwd = str_arg("cwd").unwrap_or_else(|| "/tmp".to_string());
            let session_id = core.create_workspace(&name, &cwd);
            Ok(serde_json::json!({"session_id": session_id}))
        }
        "info" => {
            Ok(serde_json::json!({
                "name": core.session(),
                "cwd": core.cwd(),
            }))
        }
        "list" => {
            Ok(serde_json::Value::Array(core.session_list()))
        }
        "snapshots" => {
            let home = resolve_nexus_home(args);
            let dir = home.join("sessions").join(&ws_name);
            let snapshots = persistence::list_snapshots(&dir)
                .map_err(NexusError::InvalidState)?;
            Ok(serde_json::Value::Array(snapshots))
        }
        "save" => {
            let name = str_arg("name").ok_or_else(|| {
                NexusError::InvalidState("session.save requires name".into())
            })?;
            let snap = core.snapshot();
            let home = resolve_nexus_home(args);
            let dir = home.join("sessions").join(&ws_name);
            let path = persistence::save_snapshot(&dir, &name, &snap)
                .map_err(NexusError::InvalidState)?;
            core.clear_dirty();
            Ok(serde_json::json!({"path": path}))
        }
        "restore" => {
            let name = str_arg("name").ok_or_else(|| {
                NexusError::InvalidState("session.restore requires name".into())
            })?;
            let home = resolve_nexus_home(args);
            let dir = home.join("sessions").join(&ws_name);
            let save = persistence::load_snapshot(&dir, &name)
                .map_err(NexusError::InvalidState)?;

            let old_pane_ids = core.layout.root.leaf_ids();
            for pane_id in &old_pane_ids {
                let _ = core.pty_kill(pane_id);
            }

            core.layout = save.layout;
            core.stacks = save.stacks;
            core.clear_dirty();
            Ok(serde_json::json!({"status": "ok"}))
        }
        "delete" => {
            let name = str_arg("name").ok_or_else(|| {
                NexusError::InvalidState("session.delete requires name".into())
            })?;
            let home = resolve_nexus_home(args);
            let dir = home.join("sessions").join(&ws_name);
            persistence::delete_snapshot(&dir, &name)
                .map_err(NexusError::InvalidState)?;
            Ok(serde_json::json!({"status": "ok"}))
        }
        _ => Err(NexusError::NotFound(format!("unknown session action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// keymap.*
// ---------------------------------------------------------------------------

fn handle_keymap(
    core: &mut NexusCore,
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "get" => {
            serde_json::to_value(core.get_keymap())
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown keymap action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// commands.*
// ---------------------------------------------------------------------------

fn handle_commands(
    core: &mut NexusCore,
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "list" => {
            serde_json::to_value(core.get_commands())
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown commands action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// layout.*
// ---------------------------------------------------------------------------

fn handle_layout(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "show" => Ok(core.layout.to_json()),

        "export" => {
            let name = str_arg("name").ok_or_else(|| {
                NexusError::InvalidState("layout.export requires name".into())
            })?;
            let description = str_arg("description");
            let scope = str_arg("scope").unwrap_or_else(|| "global".to_string());

            let export = persistence::LayoutExport {
                name: name.clone(),
                description,
                root: core.layout.root.clone(),
            };

            let layouts_dir = if scope == "project" {
                persistence::project_layouts_dir(core.cwd())
            } else {
                let home = resolve_nexus_home(args);
                home.join("layouts")
            };

            let path = persistence::save_layout_export(&layouts_dir, &export)
                .map_err(NexusError::InvalidState)?;
            Ok(serde_json::json!({"path": path}))
        }

        "import" => {
            let name = str_arg("name").ok_or_else(|| {
                NexusError::InvalidState("layout.import requires name".into())
            })?;

            let project_dir = persistence::project_layouts_dir(core.cwd());
            let home = resolve_nexus_home(args);
            let global_dir = home.join("layouts");

            let export = persistence::load_layout_export(&project_dir, &name)
                .or_else(|_| persistence::load_layout_export(&global_dir, &name))
                .map_err(|e| NexusError::NotFound(format!("layout '{name}' not found: {e}")))?;

            let old_pane_ids = core.layout.root.leaf_ids();
            for pane_id in &old_pane_ids {
                let _ = core.pty_kill(pane_id);
            }

            core.layout = crate::layout::LayoutTree::from_export(export.root);
            core.stacks = crate::stack_manager::StackManager::new();
            core.mark_dirty();

            Ok(serde_json::json!({"status": "ok"}))
        }

        "list" => {
            let project_dir = persistence::project_layouts_dir(core.cwd());
            let home = resolve_nexus_home(args);
            let global_dir = home.join("layouts");

            let mut results: Vec<serde_json::Value> = Vec::new();

            if let Ok(names) = persistence::list_layout_exports(&project_dir) {
                for name in names {
                    results.push(serde_json::json!({"name": name, "source": "project"}));
                }
            }
            if let Ok(names) = persistence::list_layout_exports(&global_dir) {
                for name in names {
                    results.push(serde_json::json!({"name": name, "source": "global"}));
                }
            }

            Ok(serde_json::Value::Array(results))
        }

        _ => Err(NexusError::NotFound(format!("unknown layout action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// capabilities.*
// ---------------------------------------------------------------------------

fn handle_capabilities(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "list" => {
            let type_filter = args.get("type").and_then(|v| v.as_str());
            Ok(core.capabilities_list(type_filter))
        }
        _ => Err(NexusError::NotFound(format!("unknown capabilities action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// nexus.*
// ---------------------------------------------------------------------------

fn handle_nexus(
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "hello" => Ok(serde_json::json!({
            "version": env!("CARGO_PKG_VERSION"),
            "protocol": 1,
        })),
        _ => Err(NexusError::NotFound(format!("unknown nexus action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// fs.*
// ---------------------------------------------------------------------------

fn handle_fs(
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "cwd" => {
            let cwd = std::env::current_dir()
                .map(|p| p.to_string_lossy().to_string())
                .map_err(|e| NexusError::Io(e.to_string()))?;
            Ok(serde_json::json!(cwd))
        }

        "list" => {
            let path = str_arg("path").ok_or_else(|| {
                NexusError::InvalidState("fs.list requires path".into())
            })?;
            let dir = std::path::PathBuf::from(&path);
            if !dir.is_dir() {
                return Err(NexusError::NotFound(format!("not a directory: {path}")));
            }

            let mut entries: Vec<serde_json::Value> = std::fs::read_dir(&dir)
                .map_err(|e| NexusError::Io(e.to_string()))?
                .filter_map(|e| e.ok())
                .filter(|e| {
                    let name = e.file_name().to_string_lossy().to_string();
                    !name.starts_with('.')
                        && name != "target"
                        && name != "node_modules"
                        && name != "__pycache__"
                })
                .map(|e| {
                    let is_dir = e.file_type().map(|t| t.is_dir()).unwrap_or(false);
                    serde_json::json!({
                        "name": e.file_name().to_string_lossy(),
                        "path": e.path().to_string_lossy(),
                        "is_dir": is_dir,
                    })
                })
                .collect();

            entries.sort_by(|a, b| {
                let a_dir = a["is_dir"].as_bool().unwrap_or(false);
                let b_dir = b["is_dir"].as_bool().unwrap_or(false);
                b_dir.cmp(&a_dir).then_with(|| {
                    let a_name = a["name"].as_str().unwrap_or("").to_lowercase();
                    let b_name = b["name"].as_str().unwrap_or("").to_lowercase();
                    a_name.cmp(&b_name)
                })
            });

            Ok(serde_json::Value::Array(entries))
        }

        "read" => {
            let path = str_arg("path").ok_or_else(|| {
                NexusError::InvalidState("fs.read requires path".into())
            })?;
            let content = std::fs::read_to_string(&path)
                .map_err(|e| NexusError::Io(format!("{path}: {e}")))?;
            Ok(serde_json::json!(content))
        }

        _ => Err(NexusError::NotFound(format!("unknown fs action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// editor.*
// ---------------------------------------------------------------------------

fn handle_editor(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "open" => {
            let path = str_arg("path").ok_or_else(|| {
                NexusError::InvalidState("editor.open requires path".into())
            })?;
            let name = str_arg("name").unwrap_or_else(|| {
                path.rsplit('/').next().unwrap_or(&path).to_string()
            });

            // Emit event so surfaces can handle the file open
            let mut payload = HashMap::new();
            payload.insert("path".to_string(), serde_json::json!(path));
            payload.insert("name".to_string(), serde_json::json!(name));
            core.publish("editor.file_opened", payload);

            Ok(serde_json::json!({"path": path, "name": name}))
        }
        _ => Err(NexusError::NotFound(format!("unknown editor action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// surface.*
// ---------------------------------------------------------------------------

fn handle_surface(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "register" => {
            let id = str_arg("id").ok_or_else(|| {
                NexusError::InvalidState("surface.register requires id".into())
            })?;
            let name = str_arg("name").unwrap_or_else(|| id.clone());
            let mode: SurfaceMode = args.get("mode")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or(SurfaceMode::Headless);
            let capabilities: SurfaceCapabilities = args.get("capabilities")
                .and_then(|v| serde_json::from_value(v.clone()).ok())
                .unwrap_or_default();

            let reg = SurfaceRegistration { id, name, mode, capabilities };
            core.surfaces.register(reg)
                .map_err(NexusError::InvalidState)?;

            // Return EngineSnapshot — everything the surface needs to render
            Ok(serde_json::json!({
                "layout": core.layout.to_json(),
                "session": core.session(),
                "cwd": core.cwd(),
                "keymap": core.get_keymap(),
                "commands": core.get_commands(),
            }))
        }

        "unregister" => {
            let id = str_arg("id").ok_or_else(|| {
                NexusError::InvalidState("surface.unregister requires id".into())
            })?;
            let removed = core.surfaces.unregister(&id);
            Ok(serde_json::json!({"removed": removed}))
        }

        "list" => {
            serde_json::to_value(core.surfaces.list())
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "capabilities" => {
            serde_json::to_value(core.surfaces.aggregate_capabilities())
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "mode" => {
            Ok(serde_json::json!({"mode": core.surfaces.active_mode()}))
        }

        _ => Err(NexusError::NotFound(format!("unknown surface action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::NexusCore;
    use crate::surface::NullMux;

    fn make_core() -> NexusCore {
        let mut core = NexusCore::new(Box::new(NullMux::new()));
        core.create_workspace("test", "/tmp");
        core
    }

    #[test]
    fn dispatch_navigate_left() {
        let mut core = make_core();
        let result = dispatch(&mut core, "navigate.left", &HashMap::new());
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_navigate_all_directions() {
        let mut core = make_core();
        for dir in &["left", "right", "up", "down"] {
            let cmd = format!("navigate.{dir}");
            assert!(dispatch(&mut core, &cmd, &HashMap::new()).is_ok());
        }
    }

    #[test]
    fn dispatch_pane_split() {
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("direction".to_string(), serde_json::json!("vertical"));
        let result = dispatch(&mut core, "pane.split", &args);
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_pane_zoom() {
        let mut core = make_core();
        let result = dispatch(&mut core, "pane.zoom", &HashMap::new());
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_unknown_domain_errors() {
        let mut core = make_core();
        let result = dispatch(&mut core, "bogus.action", &HashMap::new());
        assert!(result.is_err());
    }

    #[test]
    fn dispatch_no_dot_errors() {
        let mut core = make_core();
        let result = dispatch(&mut core, "nodot", &HashMap::new());
        assert!(result.is_err());
    }

    #[test]
    fn dispatch_unknown_action_errors() {
        let mut core = make_core();
        let result = dispatch(&mut core, "navigate.diagonal", &HashMap::new());
        assert!(result.is_err());
    }

    #[test]
    fn dispatch_layout_show() {
        let mut core = make_core();
        let result = dispatch(&mut core, "layout.show", &HashMap::new());
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_pane_list() {
        let mut core = make_core();
        let result = dispatch(&mut core, "pane.list", &HashMap::new());
        assert!(result.is_ok());
        let val = result.unwrap();
        assert!(val.is_array());
    }

    #[test]
    fn dispatch_session_info() {
        let mut core = make_core();
        let result = dispatch(&mut core, "session.info", &HashMap::new());
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_session_create() {
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("name".to_string(), serde_json::json!("test2"));
        args.insert("cwd".to_string(), serde_json::json!("/tmp"));
        let result = dispatch(&mut core, "session.create", &args);
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_session_list() {
        let mut core = make_core();
        let result = dispatch(&mut core, "session.list", &HashMap::new());
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_keymap_get() {
        let mut core = make_core();
        let result = dispatch(&mut core, "keymap.get", &HashMap::new());
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_commands_list() {
        let mut core = make_core();
        let result = dispatch(&mut core, "commands.list", &HashMap::new());
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_capabilities_list() {
        let mut core = make_core();
        let result = dispatch(&mut core, "capabilities.list", &HashMap::new());
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_pty_spawn_and_kill() {
        let ctx = nexus_core::capability::SystemContext {
            path: std::env::var("PATH").unwrap_or_default(),
            shell: "/bin/zsh".into(),
        };
        let mut core = NexusCore::with_registry(Box::new(NullMux::new()), ctx);
        core.create_workspace("test", "/tmp");

        let mut args = HashMap::new();
        args.insert("pane_id".to_string(), serde_json::json!("test-pane"));
        let spawn = dispatch(&mut core, "pty.spawn", &args);
        assert!(spawn.is_ok());

        let kill = dispatch(&mut core, "pty.kill", &args);
        assert!(kill.is_ok());
    }

    #[test]
    fn dispatch_session_save_and_restore() {
        let dir = tempfile::tempdir().unwrap();
        let mut core = make_core();
        let mut save_args = HashMap::new();
        save_args.insert("name".to_string(), serde_json::json!("my-snapshot"));
        save_args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));

        let result = dispatch(&mut core, "session.save", &save_args);
        assert!(result.is_ok());
        assert!(result.unwrap().get("path").is_some());

        core.layout.split_focused(Direction::Vertical);
        assert_eq!(core.layout.root.leaf_ids().len(), 5);

        let mut restore_args = HashMap::new();
        restore_args.insert("name".to_string(), serde_json::json!("my-snapshot"));
        restore_args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        let result = dispatch(&mut core, "session.restore", &restore_args);
        assert!(result.is_ok());
        assert_eq!(core.layout.root.leaf_ids().len(), 4);
    }

    #[test]
    fn dispatch_session_save_missing_name() {
        let mut core = make_core();
        let result = dispatch(&mut core, "session.save", &HashMap::new());
        assert!(result.is_err());
    }

    #[test]
    fn dispatch_session_snapshots() {
        let dir = tempfile::tempdir().unwrap();
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("name".to_string(), serde_json::json!("test-snap"));
        args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        dispatch(&mut core, "session.save", &args).unwrap();

        let mut list_args = HashMap::new();
        list_args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        let result = dispatch(&mut core, "session.snapshots", &list_args);
        assert!(result.is_ok());
        let arr = result.unwrap();
        assert!(arr.is_array());
        assert_eq!(arr.as_array().unwrap().len(), 1);
    }

    #[test]
    fn dispatch_session_delete() {
        let dir = tempfile::tempdir().unwrap();
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("name".to_string(), serde_json::json!("doomed"));
        args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        dispatch(&mut core, "session.save", &args).unwrap();
        let result = dispatch(&mut core, "session.delete", &args);
        assert!(result.is_ok());
    }

    #[test]
    fn dispatch_layout_export() {
        let dir = tempfile::tempdir().unwrap();
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("name".to_string(), serde_json::json!("my-layout"));
        args.insert("description".to_string(), serde_json::json!("test layout"));
        args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        let result = dispatch(&mut core, "layout.export", &args);
        assert!(result.is_ok());
        assert!(result.unwrap().get("path").is_some());
    }

    #[test]
    fn dispatch_layout_import() {
        let dir = tempfile::tempdir().unwrap();
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("name".to_string(), serde_json::json!("importable"));
        args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        dispatch(&mut core, "layout.export", &args).unwrap();

        core.layout.split_focused(Direction::Vertical);
        assert_eq!(core.layout.root.leaf_ids().len(), 5);

        let result = dispatch(&mut core, "layout.import", &args);
        assert!(result.is_ok());
        assert_eq!(core.layout.root.leaf_ids().len(), 4);
    }

    #[test]
    fn dispatch_layout_list() {
        let dir = tempfile::tempdir().unwrap();
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("name".to_string(), serde_json::json!("list-test"));
        args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        dispatch(&mut core, "layout.export", &args).unwrap();

        let mut list_args = HashMap::new();
        list_args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        let result = dispatch(&mut core, "layout.list", &list_args);
        assert!(result.is_ok());
        assert!(!result.unwrap().as_array().unwrap().is_empty());
    }

    #[test]
    fn state_mutations_set_dirty_flag() {
        let mut core = make_core();
        assert!(!core.is_dirty());

        let mut args = HashMap::new();
        args.insert("direction".to_string(), serde_json::json!("vertical"));
        dispatch(&mut core, "pane.split", &args).unwrap();
        assert!(core.is_dirty());

        core.clear_dirty();
        dispatch(&mut core, "navigate.left", &HashMap::new()).unwrap();
        assert!(core.is_dirty());
    }

    #[test]
    fn dispatch_nexus_hello() {
        let mut core = make_core();
        let result = dispatch(&mut core, "nexus.hello", &HashMap::new());
        assert!(result.is_ok());
        let val = result.unwrap();
        assert!(val.get("version").is_some());
        assert!(val.get("protocol").is_some());
    }

    #[test]
    fn dispatch_fs_cwd() {
        let mut core = make_core();
        let result = dispatch(&mut core, "fs.cwd", &HashMap::new());
        assert!(result.is_ok());
        assert!(result.unwrap().as_str().is_some());
    }

    #[test]
    fn dispatch_fs_list() {
        let dir = tempfile::tempdir().unwrap();
        // Create a test file inside
        std::fs::write(dir.path().join("hello.txt"), "hi").unwrap();
        std::fs::create_dir(dir.path().join("subdir")).unwrap();

        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("path".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        let result = dispatch(&mut core, "fs.list", &args);
        assert!(result.is_ok());
        let arr = result.unwrap();
        let entries = arr.as_array().unwrap();
        assert_eq!(entries.len(), 2);
        // Directories sort first
        assert_eq!(entries[0]["is_dir"], true);
        assert_eq!(entries[0]["name"], "subdir");
    }

    #[test]
    fn dispatch_fs_list_missing_path() {
        let mut core = make_core();
        let result = dispatch(&mut core, "fs.list", &HashMap::new());
        assert!(result.is_err());
    }

    #[test]
    fn dispatch_fs_read() {
        let dir = tempfile::tempdir().unwrap();
        let file_path = dir.path().join("test.txt");
        std::fs::write(&file_path, "hello world").unwrap();

        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("path".to_string(), serde_json::json!(file_path.to_str().unwrap()));
        let result = dispatch(&mut core, "fs.read", &args);
        assert!(result.is_ok());
        assert_eq!(result.unwrap().as_str().unwrap(), "hello world");
    }

    #[test]
    fn dispatch_fs_read_missing_file() {
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("path".to_string(), serde_json::json!("/nonexistent/path/file.txt"));
        let result = dispatch(&mut core, "fs.read", &args);
        assert!(result.is_err());
    }

    #[test]
    fn dispatch_editor_open() {
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("path".to_string(), serde_json::json!("/tmp/test.rs"));
        args.insert("name".to_string(), serde_json::json!("test.rs"));
        let result = dispatch(&mut core, "editor.open", &args);
        assert!(result.is_ok());
        let val = result.unwrap();
        assert_eq!(val["path"], "/tmp/test.rs");
        assert_eq!(val["name"], "test.rs");
    }

    #[test]
    fn dispatch_editor_open_infers_name() {
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("path".to_string(), serde_json::json!("/home/user/src/main.rs"));
        let result = dispatch(&mut core, "editor.open", &args);
        assert!(result.is_ok());
        assert_eq!(result.unwrap()["name"], "main.rs");
    }

    #[test]
    fn dispatch_surface_register() {
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("id".to_string(), serde_json::json!("tauri-main"));
        args.insert("name".to_string(), serde_json::json!("Tauri Desktop"));
        args.insert("mode".to_string(), serde_json::json!("internal"));
        args.insert("capabilities".to_string(), serde_json::json!({
            "popup": true,
            "menu": true,
            "rich_content": true,
            "internal_tiling": true,
        }));
        let result = dispatch(&mut core, "surface.register", &args);
        assert!(result.is_ok());
        let snap = result.unwrap();
        // EngineSnapshot should contain layout, session, cwd, keymap, commands
        assert!(snap.get("layout").is_some());
        assert!(snap.get("keymap").is_some());
        assert!(snap.get("commands").is_some());
    }

    #[test]
    fn dispatch_surface_register_missing_id() {
        let mut core = make_core();
        let result = dispatch(&mut core, "surface.register", &HashMap::new());
        assert!(result.is_err());
    }

    #[test]
    fn dispatch_surface_list() {
        let mut core = make_core();
        // Register a surface first
        let mut args = HashMap::new();
        args.insert("id".to_string(), serde_json::json!("cli-1"));
        args.insert("mode".to_string(), serde_json::json!("headless"));
        dispatch(&mut core, "surface.register", &args).unwrap();

        let result = dispatch(&mut core, "surface.list", &HashMap::new());
        assert!(result.is_ok());
        let list = result.unwrap();
        assert_eq!(list.as_array().unwrap().len(), 1);
        assert_eq!(list[0]["id"], "cli-1");
    }

    #[test]
    fn dispatch_surface_unregister() {
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("id".to_string(), serde_json::json!("tauri-main"));
        args.insert("mode".to_string(), serde_json::json!("internal"));
        dispatch(&mut core, "surface.register", &args).unwrap();

        let mut unreg = HashMap::new();
        unreg.insert("id".to_string(), serde_json::json!("tauri-main"));
        let result = dispatch(&mut core, "surface.unregister", &unreg);
        assert!(result.is_ok());
        assert_eq!(result.unwrap()["removed"], true);

        let list = dispatch(&mut core, "surface.list", &HashMap::new()).unwrap();
        assert_eq!(list.as_array().unwrap().len(), 0);
    }

    #[test]
    fn dispatch_surface_mode() {
        let mut core = make_core();
        let result = dispatch(&mut core, "surface.mode", &HashMap::new());
        assert!(result.is_ok());
        assert_eq!(result.unwrap()["mode"], "headless");

        let mut args = HashMap::new();
        args.insert("id".to_string(), serde_json::json!("tauri"));
        args.insert("mode".to_string(), serde_json::json!("internal"));
        dispatch(&mut core, "surface.register", &args).unwrap();

        let result = dispatch(&mut core, "surface.mode", &HashMap::new());
        assert_eq!(result.unwrap()["mode"], "internal");
    }

    #[test]
    fn dispatch_surface_capabilities() {
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("id".to_string(), serde_json::json!("tauri"));
        args.insert("mode".to_string(), serde_json::json!("internal"));
        args.insert("capabilities".to_string(), serde_json::json!({"rich_content": true}));
        dispatch(&mut core, "surface.register", &args).unwrap();

        let result = dispatch(&mut core, "surface.capabilities", &HashMap::new());
        assert!(result.is_ok());
        assert_eq!(result.unwrap()["rich_content"], true);
    }

    #[test]
    fn dispatch_surface_reject_second_delegated() {
        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("id".to_string(), serde_json::json!("tmux-0"));
        args.insert("mode".to_string(), serde_json::json!("delegated"));
        dispatch(&mut core, "surface.register", &args).unwrap();

        let mut args2 = HashMap::new();
        args2.insert("id".to_string(), serde_json::json!("sway-0"));
        args2.insert("mode".to_string(), serde_json::json!("delegated"));
        let result = dispatch(&mut core, "surface.register", &args2);
        assert!(result.is_err());
    }
}
