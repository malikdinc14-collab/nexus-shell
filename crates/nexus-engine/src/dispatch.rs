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
    _core: &mut NexusCore,
    action: &str,
    _args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    // Stub — chat backend not yet wired.
    Ok(serde_json::json!({
        "status": "ok",
        "message": format!("chat.{action} not yet wired"),
    }))
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
}
