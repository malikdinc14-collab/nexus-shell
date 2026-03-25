//! Command dispatch — single domain.action entry point for all surfaces.
//!
//! Every surface (CLI, Tauri IPC, daemon socket, tmux keybinds) routes commands
//! through `dispatch()`. Commands take the form `"domain.action"`, e.g.
//! `"navigate.left"`, `"pane.split"`, `"stack.push"`.

use std::collections::HashMap;

use nexus_core::NexusError;

use crate::core::NexusCore;
use crate::layout::{Direction, Nav, PaneType};

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

            let pane_type = str_arg("pane_type")
                .map(|s| PaneType::from_str(&s))
                .unwrap_or(PaneType::Terminal);

            let new_id = core.layout.split_focused(direction, pane_type);
            Ok(serde_json::json!({ "pane_id": new_id }))
        }

        // -- close -----------------------------------------------------------
        "close" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());

            if core.layout.close_pane(&pane_id) {
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
            Ok(core.layout.to_json())
        }

        // -- focus -----------------------------------------------------------
        "focus" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pane.focus requires pane_id arg".into())
            })?;

            if core.layout.set_focus(&pane_id) {
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
                Ok(core.layout.to_json())
            } else {
                Err(NexusError::NotFound(format!("pane not found: {pane_id}")))
            }
        }

        // -- pane.new.* ------------------------------------------------------
        _ if action.starts_with("new.") => {
            let sub = action.strip_prefix("new.").unwrap_or("terminal");
            let pane_type = PaneType::from_str(sub);
            let new_id = core.layout.split_focused(Direction::Vertical, pane_type);
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
                .map_err(|e| NexusError::InvalidState(e))?;
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
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

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
                    .map_err(|e| NexusError::InvalidState(e))?;
            } else {
                core.pty_spawn(&pane_id, cwd.as_deref())
                    .map_err(|e| NexusError::InvalidState(e))?;
            }
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
                .map_err(|e| NexusError::InvalidState(e))?;
            Ok(serde_json::Value::Null)
        }
        "resize" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.resize requires pane_id".into())
            })?;
            let cols = args.get("cols").and_then(|v| v.as_u64()).unwrap_or(80) as u16;
            let rows = args.get("rows").and_then(|v| v.as_u64()).unwrap_or(24) as u16;
            core.pty_resize(&pane_id, cols, rows)
                .map_err(|e| NexusError::InvalidState(e))?;
            Ok(serde_json::Value::Null)
        }
        "kill" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.kill requires pane_id".into())
            })?;
            core.pty_kill(&pane_id)
                .map_err(|e| NexusError::InvalidState(e))?;
            Ok(serde_json::Value::Null)
        }
        _ => Err(NexusError::NotFound(format!("unknown pty action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// session.*
// ---------------------------------------------------------------------------

fn handle_session(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "create" => {
            let name = args.get("name").and_then(|v| v.as_str()).unwrap_or("nexus");
            let cwd = args.get("cwd").and_then(|v| v.as_str()).unwrap_or("/tmp");
            let session_id = core.create_workspace(name, cwd);
            Ok(serde_json::json!({"session_id": session_id}))
        }
        "info" => {
            Ok(serde_json::json!({"name": core.session()}))
        }
        "list" => {
            Ok(serde_json::Value::Array(core.session_list()))
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
    _args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "show" => Ok(core.layout.to_json()),
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
        args.insert("pane_type".to_string(), serde_json::json!("terminal"));
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
    fn dispatch_nexus_hello() {
        let mut core = make_core();
        let result = dispatch(&mut core, "nexus.hello", &HashMap::new());
        assert!(result.is_ok());
        let val = result.unwrap();
        assert!(val.get("version").is_some());
        assert!(val.get("protocol").is_some());
    }
}
