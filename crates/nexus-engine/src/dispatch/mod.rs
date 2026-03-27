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

        "file" => handle_file(core, action, args),
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

// ---------------------------------------------------------------------------
// file.* — route file opens through the FileRouter
// ---------------------------------------------------------------------------

fn handle_file(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "open" => {
            let path = str_arg("path")
                .ok_or_else(|| NexusError::InvalidState("file.open requires path".into()))?;

            // Resolve absolute path
            let abs_path = if std::path::Path::new(&path).is_absolute() {
                path.clone()
            } else {
                let cwd = core.cwd();
                std::path::Path::new(cwd).join(&path).to_string_lossy().to_string()
            };

            let target = core.file_router.route(&abs_path);
            let open_cmd = target.open_command();
            let module_name = target.module_name();

            // Resolve target pane: explicit > existing module pane > split
            let pane_id = if let Some(explicit) = str_arg("pane_id") {
                // Caller explicitly chose a pane — but skip if it's an Explorer
                let is_explorer = resolve_active_module(core, &explicit)
                    .map_or(false, |m| m == "Explorer");
                if is_explorer {
                    resolve_file_pane(core, module_name)
                } else {
                    explicit
                }
            } else {
                resolve_file_pane(core, module_name)
            };

            // 1. Dispatch the module-specific open command
            let mut open_args = HashMap::new();
            open_args.insert("path".to_string(), serde_json::json!(&abs_path));
            open_args.insert("pane_id".to_string(), serde_json::json!(&pane_id));
            let result = dispatch(core, open_cmd, &open_args)?;

            // 2. Switch the pane's tab to the correct module
            let mut set_args = HashMap::new();
            set_args.insert("identity".to_string(), serde_json::json!(&pane_id));
            set_args.insert("name".to_string(), serde_json::json!(module_name));
            dispatch(core, "stack.set_content", &set_args)?;

            // 3. Focus the target pane
            core.layout.focused = pane_id;

            core.mark_dirty();
            Ok(result)
        }
        "route" => {
            // Query-only: which module would handle this path?
            let path = str_arg("path")
                .ok_or_else(|| NexusError::InvalidState("file.route requires path".into()))?;
            let target = core.file_router.route(&path);
            Ok(serde_json::json!({
                "module": target.module_name(),
                "command": target.open_command(),
            }))
        }
        _ => Err(NexusError::NotFound(format!("unknown file action: {action}"))),
    }
}

/// Find the best pane for opening a file in a given module.
/// Priority: last_active for that module > any existing pane with that module > split to create one.
fn resolve_file_pane(core: &mut NexusCore, module_name: &str) -> String {
    let focused = core.layout.focused.clone();

    // 1. Check last_active for this module
    if let Some(pane_id) = core.last_active.get(module_name) {
        let pane_id = pane_id.clone();
        if core.stacks.get_by_identity(&pane_id).is_some() {
            return pane_id;
        }
    }

    // 2. Find any existing pane with this module active
    for (_, stack) in core.stacks.all_stacks() {
        if let Some(tab) = stack.tabs.get(stack.active_index) {
            if tab.name == module_name {
                if let Some(ref handle) = tab.pane_handle {
                    return handle.clone();
                }
            }
        }
    }

    // 3. Find any non-Explorer, non-Terminal pane (Chooser, Info, etc.)
    for (_, stack) in core.stacks.all_stacks() {
        if let Some(tab) = stack.tabs.get(stack.active_index) {
            let name = &tab.name;
            if name != "Explorer" && name != "Terminal" && name != &focused {
                if let Some(ref handle) = tab.pane_handle {
                    return handle.clone();
                }
            }
        }
    }

    // 4. Focused pane is not an Explorer — use it
    let focused_module = resolve_active_module(core, &focused);
    if focused_module.as_deref() != Some("Explorer") {
        return focused;
    }

    // 5. Only Explorer exists — split horizontally and use the new pane
    let new_id = core.layout.split_focused(crate::layout::Direction::Horizontal);
    let (sid, _) = core.stacks.get_or_create_by_identity(&new_id, None);
    let sid = sid.clone();
    let tab = crate::stack::Tab::new(module_name)
        .with_status(crate::stack::TabStatus::Visible, true);
    core.stacks.push(&sid, tab);
    new_id
}

pub(crate) fn resolve_nexus_home(args: &HashMap<String, serde_json::Value>) -> std::path::PathBuf {
    if let Some(home) = args.get("nexus_home").and_then(|v| v.as_str()) {
        std::path::PathBuf::from(home)
    } else {
        dirs::home_dir().unwrap_or_else(|| std::path::PathBuf::from("/tmp")).join(".nexus")
    }
}
