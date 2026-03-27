//! Modular Command Dispatch
//! Decomposed from the monolithic dispatch.rs into domain-specific modules.

pub mod explorer;
pub mod editor;
pub mod surface;
pub mod system;

pub(crate) use system::handle_content;

use std::collections::HashMap;
use nexus_core::NexusError;
use crate::core::NexusCore;

/// Main entry point for all commands.
pub fn dispatch(
    core: &mut NexusCore,
    command: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    eprintln!("[INVARIANT] dispatch: command={command}");

    let (domain, action) = command
        .split_once('.')
        .ok_or_else(|| NexusError::InvalidState("command must be domain.action".into()))?;

    let result = match domain {
        "navigate" => surface::handle_navigate(core, action),
        "pane" => surface::handle_pane(core, action, args),
        "stack" => surface::handle_stack(core, action, args),
        "layout" => surface::handle_layout(core, action, args),
        "surface" => surface::handle_surface(core, action, args),
        "display" => surface::handle_display(core, action, args),

        "explorer" => explorer::handle_explorer(core, action, args),
        "fs" => explorer::handle_fs(core, action, args),

        "editor" => editor::handle_editor(core, action, args),
        "markdown" => editor::handle_markdown(core, action, args),

        "chat" => system::handle_chat(core, action, args),
        "browser" => system::handle_browser(core, action, args),
        "terminal" => system::handle_terminal(core, action, args),
        "pty" => system::handle_pty(core, action, args),
        "session" => system::handle_session(core, action, args),
        "keymap" => system::handle_keymap(core, action),
        "commands" => system::handle_commands(core, action),
        "capabilities" => system::handle_capabilities(core, action, args),
        "nexus" => system::handle_nexus(action),
        "workspace" => system::handle_workspace(core, action, args),
        "command_line" => system::handle_command_line(core, action, args),
        "info" => system::handle_info(core, action, args),
        "content" => system::handle_content(core, action, args),
        "menu" => system::handle_menu(core, action, args),

        "hud" => match action {
            "frame" | "get" => core.hud.get_best_frame()
                .and_then(|f| serde_json::to_value(&f).map_err(|e| NexusError::InvalidState(e.to_string()))),
            "frames" => core.hud.get_combined_frame()
                .and_then(|f| serde_json::to_value(&f).map_err(|e| NexusError::InvalidState(e.to_string()))),
            _ => Err(NexusError::NotFound(format!("unknown hud action: {action}"))),
        },
        
        _ => Err(NexusError::NotFound(format!("unknown domain: {domain}"))),
    };

    match &result {
        Ok(val) => {
            let has_root = val.get("root").is_some();
            let has_focused = val.get("focused").is_some();
            let status = val.get("status").and_then(|v| v.as_str()).unwrap_or("(none)");
            eprintln!("[INVARIANT] dispatch result: command={command}, has_root={has_root}, has_focused={has_focused}, status={status}");
        }
        Err(e) => {
            eprintln!("[INVARIANT] dispatch ERROR: command={command}, err={e}");
        }
    }

    result
}

// ---------------------------------------------------------------------------
// Shared Internal Helpers
// ---------------------------------------------------------------------------

pub(crate) fn resolve_active_module(core: &NexusCore, pane_id: &str) -> Option<String> {
    let (_, stack) = core.stacks.get_by_identity(pane_id)?;
    let tab = stack.tabs.get(stack.active_index)?;
    Some(tab.name.clone())
}

pub(crate) fn update_last_active(core: &mut NexusCore) {
    let focused = core.layout.focused.clone();
    if let Some(module) = resolve_active_module(core, &focused) {
        core.last_active.insert(module, focused);
    }
}

pub(crate) fn resolve_editor_pane(core: &NexusCore) -> String {
    if let Some(pane_id) = core.last_active.get("Editor") {
        if let Some((_, stack)) = core.stacks.get_by_identity(pane_id) {
            if stack.tabs.iter().any(|t| t.name == "Editor") {
                return pane_id.clone();
            }
        }
    }
    for (_, stack) in core.stacks.all_stacks() {
        if stack.role.as_deref() == Some("editor") {
            if let Some(tab) = stack.tabs.first() {
                if let Some(ref handle) = tab.pane_handle {
                    return handle.clone();
                }
            }
        }
    }
    core.layout.focused.clone()
}

pub(crate) fn resolve_nexus_home(args: &HashMap<String, serde_json::Value>) -> std::path::PathBuf {
    if let Some(home) = args.get("nexus_home").and_then(|v| v.as_str()) {
        std::path::PathBuf::from(home)
    } else {
        dirs::home_dir().unwrap_or_else(|| std::path::PathBuf::from("/tmp")).join(".nexus")
    }
}
