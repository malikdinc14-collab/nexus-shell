use std::collections::HashMap;
use nexus_core::NexusError;
use nexus_core::surface::{SurfaceCapabilities, SurfaceMode, SurfaceRegistration};
use crate::core::NexusCore;
use crate::layout::{Direction, Nav};
use crate::persistence;
use super::{update_last_active, resolve_nexus_home, handle_content};

// ---------------------------------------------------------------------------
// navigate.*
// ---------------------------------------------------------------------------

pub fn handle_navigate(
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

pub fn handle_pane(
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

        // -- swap (direct: swap two panes by id) --------------------------------
        "swap" => {
            let pane_id = args.get("pane_id")
                .and_then(|v| v.as_str())
                .ok_or_else(|| NexusError::InvalidState("pane.swap requires pane_id".into()))?
                .to_string();
            let target_id = args.get("target_id")
                .and_then(|v| v.as_str())
                .ok_or_else(|| NexusError::InvalidState("pane.swap requires target_id".into()))?
                .to_string();
            core.layout.root.swap_leaves(&pane_id, &target_id);
            core.mark_dirty();
            Ok(core.layout.to_json())
        }

        // -- swap directional (swap focused with neighbor) ----------------------
        "swap_left" | "swap_right" | "swap_up" | "swap_down" => {
            let nav = match action {
                "swap_left" => Nav::Left,
                "swap_right" => Nav::Right,
                "swap_up" => Nav::Up,
                "swap_down" => Nav::Down,
                _ => unreachable!(),
            };
            core.layout.swap_toward(nav);
            core.mark_dirty();
            Ok(core.layout.to_json())
        }

        // -- grow (keyboard resize) -------------------------------------------
        "grow_left" | "grow_right" | "grow_up" | "grow_down" => {
            let nav = match action {
                "grow_left" => Nav::Left,
                "grow_right" => Nav::Right,
                "grow_up" => Nav::Up,
                "grow_down" => Nav::Down,
                _ => unreachable!(),
            };
            core.layout.grow(nav);
            core.mark_dirty();
            Ok(core.layout.to_json())
        }

        // -- move (detach + reinsert) -----------------------------------------
        "move_left" | "move_right" | "move_up" | "move_down" => {
            let nav = match action {
                "move_left" => Nav::Left,
                "move_right" => Nav::Right,
                "move_up" => Nav::Up,
                "move_down" => Nav::Down,
                _ => unreachable!(),
            };
            core.layout.move_pane(nav);
            core.mark_dirty();
            Ok(core.layout.to_json())
        }

        _ => Err(NexusError::NotFound(format!("unknown pane action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// stack.*
// ---------------------------------------------------------------------------

pub fn handle_stack(
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

        let has_content_tabs = super::resolve_active_module(core, &pane_id)
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
// layout.*
// ---------------------------------------------------------------------------

pub fn handle_layout(
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

            let path = persistence::save_layout_export(&layouts_dir, &export)?;
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

        // -- equalize (reset all ratios to 0.5) ------------------------------
        "equalize" => {
            core.layout.equalize();
            core.mark_dirty();
            Ok(core.layout.to_json())
        }

        // -- rotate (flip parent split H<->V) --------------------------------
        "rotate" => {
            core.layout.rotate();
            core.mark_dirty();
            Ok(core.layout.to_json())
        }

        _ => Err(NexusError::NotFound(format!("unknown layout action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// surface.*
// ---------------------------------------------------------------------------

pub fn handle_surface(
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
            core.surfaces.register(reg)?;

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

pub fn handle_display(
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
