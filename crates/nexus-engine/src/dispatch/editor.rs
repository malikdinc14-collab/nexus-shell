use std::collections::HashMap;
use nexus_core::NexusError;
use crate::core::NexusCore;

// ---------------------------------------------------------------------------
// editor.*
// ---------------------------------------------------------------------------

pub fn handle_editor(
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

            let buffer = core.editor.open(&pane_id, &path)?;

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
            core.editor.edit(&pane_id, &content)?;
            Ok(serde_json::json!({"status": "ok", "modified": true}))
        }
        "save" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            core.editor.save(&pane_id)?;
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
// markdown.*
// ---------------------------------------------------------------------------

pub fn handle_markdown(
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

            // 1. Load node in engine (auto-opens vault from cwd)
            let cwd = core.cwd().to_string();
            let node = core.richtext.load_node(&pane_id, &path, &cwd)?;

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
