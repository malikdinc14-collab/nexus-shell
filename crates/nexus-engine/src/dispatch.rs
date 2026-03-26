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
        "browser" => handle_browser(core, action, args),
        "terminal" => handle_terminal(core, action, args),
        "pty" => handle_pty(core, action, args),
        "session" => handle_session(core, action, args),
        "keymap" => handle_keymap(core, action),
        "commands" => handle_commands(core, action),
        "layout" => handle_layout(core, action, args),
        "capabilities" => handle_capabilities(core, action, args),
        "nexus" => handle_nexus(action),
        "fs" => handle_fs(core, action, args),
        "content" => handle_content(core, action, args),
        "explorer" => handle_explorer(core, action, args),
        "editor" => handle_editor(core, action, args),
        "surface" => handle_surface(core, action, args),
        "display" => handle_display(core, action, args),
        "command_line" => handle_command_line(core, action, args),
        "menu" => handle_menu(core, action, args),
        "info" => handle_info(core, action, args),
        "markdown" => handle_markdown(core, action, args),
        "hud" => {
            let val = serde_json::to_value(args).unwrap_or(serde_json::Value::Null);
            core.handle_hud(action, &val)
        }
        _ => Err(NexusError::NotFound(format!("unknown domain: {domain}"))),
    }
}

impl NexusCore {
    fn handle_hud(&self, action: &str, _args: &serde_json::Value) -> Result<serde_json::Value, NexusError> {
        match action {
            "frame" => {
                let frame = self.hud.get_best_frame()?;
                serde_json::to_value(&frame)
                    .map_err(|e| NexusError::InvalidState(e.to_string()))
            }
            "list" => {
                let frames = self.hud.get_combined_frame()?;
                serde_json::to_value(&frames)
                    .map_err(|e| NexusError::InvalidState(e.to_string()))
            }
            _ => Err(NexusError::NotFound(format!("unknown hud action: {action}"))),
        }
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

    // Track last-active module for this pane
    update_last_active(core);

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
            // Give the new pane a Chooser tab so user picks what goes there
            let (sid, _) = core.stacks.get_or_create_by_identity(&new_id, None);
            let sid = sid.clone();
            let tab = crate::stack::Tab::new("Chooser")
                .with_status(crate::stack::TabStatus::Visible, true);
            core.stacks.push(&sid, tab);
            core.mark_dirty();
            Ok(core.layout.to_json())
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
                update_last_active(core);
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
            let tab = crate::stack::Tab::new(&tab_name);
            let (stack_id, _) = core.stacks.get_or_create_by_identity(&new_id, None);
            core.stacks.push(&stack_id, tab);
            core.mark_dirty();
            Ok(core.layout.to_json())
        }

        // -- role ----------------------------------------------------------------
        "set_role" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            let role = str_arg("role").ok_or_else(|| {
                NexusError::InvalidState("pane.set_role requires role".into())
            })?;
            match core.stacks.get_by_identity_mut(&pane_id) {
                Some((_sid, stack)) => {
                    stack.role = Some(role.clone());
                    Ok(serde_json::json!({"status": "ok", "role": role}))
                }
                None => Err(NexusError::NotFound(format!("no stack for pane: {pane_id}"))),
            }
        }

        "get_role" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            match core.stacks.get_by_identity(&pane_id) {
                Some((_sid, stack)) => {
                    Ok(serde_json::json!({"role": stack.role}))
                }
                None => Ok(serde_json::json!({"role": null})),
            }
        }

        "clear_role" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            match core.stacks.get_by_identity_mut(&pane_id) {
                Some((_sid, stack)) => {
                    stack.role = None;
                    Ok(serde_json::json!({"status": "ok"}))
                }
                None => Err(NexusError::NotFound(format!("no stack for pane: {pane_id}"))),
            }
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
    // Unified prev/next: try content tabs first, fall through to module tabs
    if action == "prev" || action == "next" {
        let pane_id = args
            .get("identity")
            .and_then(|v| v.as_str())
            .map(String::from)
            .unwrap_or_else(|| core.layout.focused.clone());

        let has_content_tabs = resolve_active_module(core, &pane_id)
            .and_then(|module| {
                use crate::content_tabs::TabProvider;
                match module.as_str() {
                    "Editor" => core.editor.content_tabs(&pane_id),
                    "Terminal" => core.terminal.content_tabs(&pane_id),
                    "Chat" => core.chat.content_tabs(&pane_id),
                    _ => None,
                }
            })
            .map(|s| s.tabs.len() > 1)
            .unwrap_or(false);

        if has_content_tabs {
            let content_action = if action == "next" { "next" } else { "prev" };
            let mut content_args = HashMap::new();
            content_args.insert("pane_id".to_string(), serde_json::json!(pane_id));
            return handle_content(core, content_action, &content_args);
        }
        // Fall through to module-level tab switching
    }

    // Auto-inject focused pane as identity if not provided (keyboard shortcuts omit it)
    let mut args = args.clone();
    if !args.contains_key("identity") {
        args.insert(
            "identity".to_string(),
            serde_json::Value::String(core.layout.focused.clone()),
        );
    }

    // Auto-generate pane_id for push if not provided (keyboard shortcuts omit it)
    if action == "push" && !args.contains_key("pane_id") {
        args.insert(
            "pane_id".to_string(),
            serde_json::Value::String(format!("pane_{}", uuid::Uuid::new_v4())),
        );
    }

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
        // Update last_active when module tab changes (e.g. set_content)
        if action == "set_content" {
            update_last_active(core);
        }
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
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "send" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("chat.send requires pane_id".into())
            })?;
            let message = str_arg("message").ok_or_else(|| {
                NexusError::InvalidState("chat.send requires message".into())
            })?;
            let cwd = str_arg("cwd").unwrap_or_else(|| "/tmp".into());

            // Also delegate to legacy chat_send if registry has a chat adapter
            if core.registry.is_some() {
                let _ = core.chat_send(&pane_id, &message, &cwd);
            }

            let conv = core.chat.send(&pane_id, &message, &cwd)
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&conv)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "history" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("chat.history requires pane_id".into())
            })?;
            match core.chat.history(&pane_id) {
                Some(conv) => serde_json::to_value(conv)
                    .map_err(|e| NexusError::InvalidState(e.to_string())),
                None => Ok(serde_json::json!({"messages": []})),
            }
        }
        "clear" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("chat.clear requires pane_id".into())
            })?;
            let cleared = core.chat.clear(&pane_id);
            Ok(serde_json::json!({"cleared": cleared}))
        }
        "state" => {
            let state = core.chat.state();
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown chat action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// browser.*
// ---------------------------------------------------------------------------

fn handle_browser(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "open" => {
            let url = str_arg("url").unwrap_or_else(|| "https://google.com".into());
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());

            // 1. Create session in engine
            let session = core.browser.open(&pane_id, &url)?;

            // 2. Ensure the pane has a Browser tab
            let (sid, stack) = core.stacks.get_or_create_by_identity(&pane_id, None);
            let sid = sid.clone();

            // If active tab isn't Browser, push or switch to it
            let has_browser = stack.tabs.iter().any(|t| t.name == "Browser");
            if !has_browser {
                let tab = crate::stack::Tab::new("Browser")
                    .with_status(crate::stack::TabStatus::Visible, true);
                core.stacks.push(&sid, tab);
            } else {
                // Find index and switch
                let idx = stack.tabs.iter().position(|t| t.name == "Browser").unwrap();
                let mut switch_args = HashMap::new();
                switch_args.insert("identity".into(), pane_id.clone());
                switch_args.insert("index".into(), idx.to_string());
                core.handle_stack_op("switch", &switch_args);
            }

            core.mark_dirty();
            serde_json::to_value(&session)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "navigate" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            let url = str_arg("url").ok_or_else(|| {
                NexusError::InvalidState("browser.navigate requires url".into())
            })?;

            core.browser.navigate(&pane_id, &url)?;
            core.mark_dirty();
            Ok(serde_json::json!({"status": "ok"}))
        }
        "state" => {
            let state = core.browser.state();
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown browser action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// markdown.*
// ---------------------------------------------------------------------------

fn handle_markdown(
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
                NexusError::InvalidState("markdown.open requires path".into())
            })?;
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());

            // 1. Load node in engine
            let node = core.richtext.load_node(&pane_id, &path)?;

            // 2. Ensure pane has a RichText tab
            let (sid, stack) = core.stacks.get_or_create_by_identity(&pane_id, None);
            let sid = sid.clone();

            let has_richtext = stack.tabs.iter().any(|t| t.name == "RichText");
            if !has_richtext {
                let tab = crate::stack::Tab::new("RichText")
                    .with_status(crate::stack::TabStatus::Visible, true);
                core.stacks.push(&sid, tab);
            } else {
                let idx = stack.tabs.iter().position(|t| t.name == "RichText").unwrap();
                let mut switch_args = HashMap::new();
                switch_args.insert("identity".into(), pane_id.clone());
                switch_args.insert("index".into(), idx.to_string());
                core.handle_stack_op("switch", &switch_args);
            }

            core.mark_dirty();
            serde_json::to_value(&node)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "save" => {
            // Stub for now
            Ok(serde_json::json!({"status": "ok"}))
        }
        "state" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            let node = core.richtext.state(&pane_id)?;
            serde_json::to_value(&node)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown markdown action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// terminal.*  (ABC orchestrator — session metadata + backend selection)
// ---------------------------------------------------------------------------

fn handle_terminal(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "state" => {
            let state = core.terminal.state();
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "info" => {
            let info = core.terminal.info();
            serde_json::to_value(&info)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "session" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("terminal.session requires pane_id".into())
            })?;
            match core.terminal.session(&pane_id) {
                Some(s) => serde_json::to_value(s)
                    .map_err(|e| NexusError::InvalidState(e.to_string())),
                None => Err(NexusError::NotFound(format!("no terminal session: {pane_id}"))),
            }
        }
        "register" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("terminal.register requires pane_id".into())
            })?;
            let cwd = str_arg("cwd");
            let session = core.terminal.register_session(&pane_id, cwd.as_deref());
            serde_json::to_value(session)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "update" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("terminal.update requires pane_id".into())
            })?;
            let title = str_arg("title");
            let pid = args.get("pid").and_then(|v| v.as_u64()).map(|p| p as u32);
            let cwd = str_arg("cwd");
            core.terminal.update_session(&pane_id, title.as_deref(), pid, cwd.as_deref());
            Ok(serde_json::json!({"status": "ok"}))
        }
        "remove" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("terminal.remove requires pane_id".into())
            })?;
            let removed = core.terminal.remove_session(&pane_id);
            Ok(serde_json::json!({"removed": removed}))
        }
        _ => Err(NexusError::NotFound(format!("unknown terminal action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// pty.*  (low-level PTY I/O — kept for backward compat, delegates to Mux or PtyManager)
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

        // -- template: apply a built-in layout template ----------------------
        "template" => {
            let name = str_arg("name").ok_or_else(|| {
                NexusError::InvalidState("layout.template requires name".into())
            })?;
            let template = crate::templates::get_template(&name)
                .ok_or_else(|| NexusError::NotFound(format!("template not found: {name}")))?;

            // Clean up old PTYs
            let old_pane_ids = core.layout.root.leaf_ids();
            for pane_id in &old_pane_ids {
                let _ = core.pty_kill(pane_id);
            }

            // Apply template layout (from_export regenerates IDs)
            core.layout = crate::layout::LayoutTree::from_export(template.layout);

            // Init stacks from template
            core.stacks = crate::stack_manager::StackManager::new();
            for (pane_id, tab_name) in &template.stacks {
                let (sid, stack) = core.stacks.get_or_create_by_identity(pane_id, None);
                let sid = sid.clone();
                if stack.tabs.is_empty() {
                    let tab = crate::stack::Tab::new(tab_name)
                        .with_status(crate::stack::TabStatus::Visible, true);
                    core.stacks.push(&sid, tab);
                }
            }

            core.mark_dirty();
            Ok(core.layout.to_json())
        }

        // -- templates: list available built-in templates --------------------
        "templates" => {
            let list: Vec<serde_json::Value> = crate::templates::builtin_templates()
                .iter()
                .map(|t| serde_json::json!({
                    "name": t.name,
                    "description": t.description,
                }))
                .collect();
            Ok(serde_json::Value::Array(list))
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
    core: &NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "cwd" => {
            // Return the engine's workspace CWD (set via --cwd), not process CWD
            let cwd = core.cwd().to_string();
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
// explorer.*
// ---------------------------------------------------------------------------

fn handle_explorer(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        // Full tree state — surface renders this directly
        "tree" => {
            let state = core.explorer.tree()
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Flat listing of a single directory
        "list" => {
            let path = str_arg("path")
                .unwrap_or_else(|| core.explorer.root().to_string());
            let entries = core.explorer.list(&path)
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&entries)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Navigate to a new root
        "navigate" => {
            let path = str_arg("path").ok_or_else(|| {
                NexusError::InvalidState("explorer.navigate requires path".into())
            })?;
            core.explorer.navigate(&path);
            let state = core.explorer.tree()
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Go up one directory
        "up" => {
            core.explorer.up();
            let state = core.explorer.tree()
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Toggle directory expanded/collapsed
        "toggle" => {
            let path = str_arg("path").ok_or_else(|| {
                NexusError::InvalidState("explorer.toggle requires path".into())
            })?;
            let expanded = core.explorer.toggle(&path);
            let state = core.explorer.tree()
                .map_err(NexusError::InvalidState)?;
            let mut val = serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))?;
            val["toggled"] = serde_json::json!(expanded);
            Ok(val)
        }

        // Toggle hidden files
        "hidden" => {
            let show = core.explorer.toggle_hidden();
            let state = core.explorer.tree()
                .map_err(NexusError::InvalidState)?;
            let mut val = serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))?;
            val["show_hidden"] = serde_json::json!(show);
            Ok(val)
        }

        // Search — delegates to backend
        "search" => {
            let query = str_arg("query").ok_or_else(|| {
                NexusError::InvalidState("explorer.search requires query".into())
            })?;
            let entries = core.explorer.search(&query)
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&entries)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Cursor navigation — keyboard-driven file tree browsing
        "cursor_down" => {
            let count = core.explorer.tree()
                .map_err(NexusError::InvalidState)?
                .entries.len();
            core.explorer.cursor_down(count);
            let state = core.explorer.tree()
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "cursor_up" => {
            core.explorer.cursor_up();
            let state = core.explorer.tree()
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "cursor_toggle" => {
            // Get entry at cursor before toggling
            let pre_state = core.explorer.tree()
                .map_err(NexusError::InvalidState)?;
            let entry = pre_state.entries.get(core.explorer.cursor_index()).cloned();

            if let Some(ref e) = entry {
                if !e.entry.is_dir {
                    // File — open in editor via command_line routing
                    let path = e.entry.path.clone();
                    let mut ed_args = HashMap::new();
                    ed_args.insert("raw".to_string(), serde_json::json!(format!("e {path}")));
                    let _ = dispatch(core, "command_line.execute", &ed_args);
                    // Return current state unchanged
                    let state = core.explorer.tree()
                        .map_err(NexusError::InvalidState)?;
                    return serde_json::to_value(&state)
                        .map_err(|e| NexusError::InvalidState(e.to_string()));
                }
            }

            // Directory — toggle expand/collapse
            let state = core.explorer.cursor_toggle()
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "cursor_collapse" => {
            let state = core.explorer.cursor_collapse()
                .map_err(NexusError::InvalidState)?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        _ => Err(NexusError::NotFound(format!("unknown explorer action: {action}"))),
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
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());

            let buffer = core.editor.open(&pane_id, &path)
                .map_err(NexusError::InvalidState)?;

            // Emit event so surfaces know a file was opened
            let mut payload = HashMap::new();
            payload.insert("path".to_string(), serde_json::json!(buffer.path));
            payload.insert("name".to_string(), serde_json::json!(buffer.name));
            payload.insert("pane_id".to_string(), serde_json::json!(pane_id));
            core.publish("editor.file_opened", payload);

            serde_json::to_value(&buffer)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "read" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            match core.editor.buffer(&pane_id) {
                Some(buf) => serde_json::to_value(buf)
                    .map_err(|e| NexusError::InvalidState(e.to_string())),
                None => Err(NexusError::NotFound(format!("no buffer in {pane_id}"))),
            }
        }
        "edit" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            let content = str_arg("content").ok_or_else(|| {
                NexusError::InvalidState("editor.edit requires content".into())
            })?;
            core.editor.edit(&pane_id, &content)
                .map_err(NexusError::InvalidState)?;
            Ok(serde_json::json!({"status": "ok", "modified": true}))
        }
        "save" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            core.editor.save(&pane_id)
                .map_err(NexusError::InvalidState)?;
            Ok(serde_json::json!({"status": "ok"}))
        }
        "close" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            let closed = core.editor.close(&pane_id);
            Ok(serde_json::json!({"closed": closed}))
        }
        "state" => {
            let state = core.editor.state();
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
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
// display.*
// ---------------------------------------------------------------------------

fn handle_display(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "get" => serde_json::to_value(core.get_display())
            .map_err(|e| NexusError::InvalidState(e.to_string())),

        "set" => {
            let key = str_arg("key")
                .ok_or_else(|| NexusError::InvalidState("display.set requires key".into()))?;
            let value = str_arg("value")
                .ok_or_else(|| NexusError::InvalidState("display.set requires value".into()))?;
            core.set_display_key(&key, &value);
            serde_json::to_value(core.get_display())
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "gaps" => {
            core.cycle_gaps();
            serde_json::to_value(core.get_display())
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "transparent" => {
            core.toggle_transparent();
            serde_json::to_value(core.get_display())
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        _ => Err(NexusError::NotFound(format!("unknown display action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// command_line.*
// ---------------------------------------------------------------------------

fn handle_command_line(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "execute" => {
            let raw = args
                .get("raw")
                .and_then(|v| v.as_str())
                .ok_or_else(|| NexusError::InvalidState("command_line.execute requires raw".into()))?;

            let parts: Vec<&str> = raw.split_whitespace().collect();
            if parts.is_empty() {
                return Ok(serde_json::json!({"status": "empty"}));
            }

            match parts[0] {
                "q" => dispatch(core, "pane.close", &HashMap::new()),
                "wq" => {
                    // Best-effort save, then close
                    let _ = dispatch(core, "session.save", args);
                    dispatch(core, "pane.close", &HashMap::new())
                }
                // :e <path> — open file in editor, routed to best pane
                "e" | "edit" if parts.len() >= 2 => {
                    let path = parts[1..].join(" ");
                    let target_pane = resolve_editor_pane(core);

                    let mut ed_args = HashMap::new();
                    ed_args.insert("path".to_string(), serde_json::json!(path));
                    ed_args.insert("pane_id".to_string(), serde_json::json!(&target_pane));
                    let result = dispatch(core, "editor.open", &ed_args)?;

                    // Ensure the target pane has Editor as active tab
                    let mut set_args = HashMap::new();
                    set_args.insert("identity".to_string(), serde_json::json!(&target_pane));
                    set_args.insert("name".to_string(), serde_json::json!("Editor"));
                    let _ = dispatch(core, "stack.set_content", &set_args);

                    // Focus the target pane
                    core.layout.set_focus(&target_pane);
                    core.mark_dirty();

                    Ok(result)
                }
                "set" if parts.len() >= 3 => {
                    let mut set_args = HashMap::new();
                    set_args.insert("key".to_string(), serde_json::json!(parts[1]));
                    set_args.insert("value".to_string(), serde_json::json!(parts[2..].join(" ")));
                    dispatch(core, "display.set", &set_args)
                }
                _ => {
                    // Try as a domain.action passthrough
                    dispatch(core, raw, &HashMap::new())
                }
            }
        }
        _ => Err(NexusError::NotFound(format!("unknown command_line action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// menu.*
// ---------------------------------------------------------------------------

fn handle_menu(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "get" => {
            let context = str_arg("context").unwrap_or_else(|| "home".into());
            let list = core.menu.get(&context);
            Ok(serde_json::to_value(&list).unwrap_or_default())
        }
        "navigate" => {
            let context = str_arg("context")
                .ok_or_else(|| NexusError::InvalidState("menu.navigate requires context".into()))?;
            let list = core.menu.navigate(&context);
            Ok(serde_json::to_value(&list).unwrap_or_default())
        }
        "back" => {
            let list = core.menu.back();
            Ok(serde_json::to_value(&list).unwrap_or_default())
        }
        "execute" => {
            let item_type = str_arg("type")
                .ok_or_else(|| NexusError::InvalidState("menu.execute requires type".into()))?;
            let payload = str_arg("payload").unwrap_or_default();

            match item_type.as_str() {
                "module" => {
                    // Set the active tab's content to this module
                    let mut set_args = HashMap::new();
                    set_args.insert("identity".into(), serde_json::json!(core.layout.focused));
                    set_args.insert("name".into(), serde_json::json!(payload));
                    dispatch(core, "stack.set_content", &set_args)
                }
                "action" => {
                    // Payload is a domain.action command — passthrough
                    dispatch(core, &payload, &HashMap::new())
                }
                "folder" => {
                    // Navigate into subfolder
                    let list = core.menu.navigate(&payload);
                    Ok(serde_json::to_value(&list).unwrap_or_default())
                }
                "settings" => {
                    // Open file in editor — payload is the file path
                    let mut ed_args = HashMap::new();
                    ed_args.insert("path".into(), serde_json::json!(payload));
                    dispatch(core, "editor.open", &ed_args)
                }
                _ => Ok(serde_json::json!({"status": "unknown_type", "type": item_type})),
            }
        }
        _ => Err(NexusError::NotFound(format!("unknown menu action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// info.*
// ---------------------------------------------------------------------------

fn handle_info(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "get" => {
            let section = args
                .get("section")
                .and_then(|v| v.as_str())
                .unwrap_or("all");
            if section == "all" {
                let data = crate::info::collect(core);
                Ok(serde_json::to_value(&data).unwrap_or_default())
            } else {
                Ok(crate::info::collect_section(core, section))
            }
        }
        _ => Err(NexusError::NotFound(format!("unknown info action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// content.*  (TabProvider — content tabs within modules)
// ---------------------------------------------------------------------------

fn resolve_active_module(core: &NexusCore, pane_id: &str) -> Option<String> {
    let (_, stack) = core.stacks.get_by_identity(pane_id)?;
    let tab = stack.tabs.get(stack.active_index)?;
    Some(tab.name.clone())
}

/// Update last_active tracking for the currently focused pane's module.
fn update_last_active(core: &mut NexusCore) {
    let focused = core.layout.focused.clone();
    if let Some(module) = resolve_active_module(core, &focused) {
        core.last_active.insert(module, focused);
    }
}

/// Find the best pane to open a file in.
/// Priority: last_active["Editor"] > any stack with role "editor" > focused pane.
fn resolve_editor_pane(core: &NexusCore) -> String {
    // 1. Check last_active["Editor"] — verify it still has an Editor tab
    if let Some(pane_id) = core.last_active.get("Editor") {
        if let Some((_, stack)) = core.stacks.get_by_identity(pane_id) {
            if stack.tabs.iter().any(|t| t.name == "Editor") {
                return pane_id.clone();
            }
        }
    }
    // 2. Check any stack with role "editor"
    for (_, stack) in core.stacks.all_stacks() {
        if stack.role.as_deref() == Some("editor") {
            if let Some(tab) = stack.tabs.first() {
                if let Some(ref handle) = tab.pane_handle {
                    return handle.clone();
                }
            }
        }
    }
    // 3. Fallback: focused pane
    core.layout.focused.clone()
}

fn handle_content(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    use crate::content_tabs::TabProvider;

    let pane_id = args
        .get("pane_id")
        .and_then(|v| v.as_str())
        .map(String::from)
        .unwrap_or_else(|| core.layout.focused.clone());

    let module = resolve_active_module(core, &pane_id)
        .unwrap_or_default();

    match action {
        "tabs" => {
            let state = match module.as_str() {
                "Editor" => core.editor.content_tabs(&pane_id),
                "Terminal" => core.terminal.content_tabs(&pane_id),
                "Chat" => core.chat.content_tabs(&pane_id),
                _ => None,
            };
            match state {
                Some(s) => serde_json::to_value(&s)
                    .map_err(|e| NexusError::InvalidState(e.to_string())),
                None => Ok(serde_json::json!(null)),
            }
        }

        "switch" => {
            let index = args.get("index")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| NexusError::InvalidState("content.switch requires index".into()))?
                as usize;

            let state = match module.as_str() {
                "Editor" => core.editor.switch_content_tab(&pane_id, index),
                "Terminal" => core.terminal.switch_content_tab(&pane_id, index),
                "Chat" => core.chat.switch_content_tab(&pane_id, index),
                _ => Err(format!("module {module} has no content tabs")),
            }.map_err(NexusError::InvalidState)?;

            // Emit event
            let mut payload = HashMap::new();
            payload.insert("pane_id".to_string(), serde_json::json!(pane_id));
            payload.insert("state".to_string(), serde_json::to_value(&state).unwrap_or_default());
            core.publish("content.changed", payload);

            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "close" => {
            let index = args.get("index")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| NexusError::InvalidState("content.close requires index".into()))?
                as usize;

            let result = match module.as_str() {
                "Editor" => core.editor.close_content_tab(&pane_id, index),
                "Terminal" => core.terminal.close_content_tab(&pane_id, index),
                "Chat" => core.chat.close_content_tab(&pane_id, index),
                _ => Err(format!("module {module} has no content tabs")),
            }.map_err(NexusError::InvalidState)?;

            // Emit event
            let mut payload = HashMap::new();
            payload.insert("pane_id".to_string(), serde_json::json!(pane_id));
            core.publish("content.changed", payload);

            match result {
                Some(state) => serde_json::to_value(&state)
                    .map_err(|e| NexusError::InvalidState(e.to_string())),
                None => Ok(serde_json::json!({"empty": true})),
            }
        }

        "next" | "prev" => {
            let state = match module.as_str() {
                "Editor" => core.editor.content_tabs(&pane_id),
                "Terminal" => core.terminal.content_tabs(&pane_id),
                "Chat" => core.chat.content_tabs(&pane_id),
                _ => None,
            };

            let state = state.ok_or_else(|| NexusError::InvalidState("no content tabs".into()))?;
            if state.tabs.is_empty() {
                return Err(NexusError::InvalidState("no content tabs".into()));
            }

            let new_index = if action == "next" {
                (state.active + 1) % state.tabs.len()
            } else {
                if state.active == 0 { state.tabs.len() - 1 } else { state.active - 1 }
            };

            let new_state = match module.as_str() {
                "Editor" => core.editor.switch_content_tab(&pane_id, new_index),
                "Terminal" => core.terminal.switch_content_tab(&pane_id, new_index),
                "Chat" => core.chat.switch_content_tab(&pane_id, new_index),
                _ => Err("unreachable".into()),
            }.map_err(NexusError::InvalidState)?;

            let mut payload = HashMap::new();
            payload.insert("pane_id".to_string(), serde_json::json!(pane_id));
            payload.insert("state".to_string(), serde_json::to_value(&new_state).unwrap_or_default());
            core.publish("content.changed", payload);

            serde_json::to_value(&new_state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        _ => Err(NexusError::NotFound(format!("unknown content action: {action}"))),
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
        assert_eq!(core.layout.root.leaf_ids().len(), 2);

        let mut restore_args = HashMap::new();
        restore_args.insert("name".to_string(), serde_json::json!("my-snapshot"));
        restore_args.insert("_nexus_home".to_string(), serde_json::json!(dir.path().to_str().unwrap()));
        let result = dispatch(&mut core, "session.restore", &restore_args);
        assert!(result.is_ok());
        assert_eq!(core.layout.root.leaf_ids().len(), 1);
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
        assert_eq!(core.layout.root.leaf_ids().len(), 2);

        let result = dispatch(&mut core, "layout.import", &args);
        assert!(result.is_ok());
        assert_eq!(core.layout.root.leaf_ids().len(), 1);
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
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("test.rs");
        std::fs::write(&file, "fn main() {}").unwrap();

        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("path".to_string(), serde_json::json!(file.to_str().unwrap()));
        let result = dispatch(&mut core, "editor.open", &args);
        assert!(result.is_ok());
        let val = result.unwrap();
        assert_eq!(val["name"], "test.rs");
        assert!(val["content"].as_str().unwrap().contains("fn main"));
    }

    #[test]
    fn dispatch_editor_open_infers_name() {
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("main.rs");
        std::fs::write(&file, "// hello").unwrap();

        let mut core = make_core();
        let mut args = HashMap::new();
        args.insert("path".to_string(), serde_json::json!(file.to_str().unwrap()));
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
