use std::collections::HashMap;
use nexus_core::NexusError;
use crate::core::NexusCore;
use super::dispatch;

// ---------------------------------------------------------------------------
// fs.*
// ---------------------------------------------------------------------------

pub fn handle_fs(
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

pub fn handle_explorer(
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
            let state = core.explorer.tree()?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Flat listing of a single directory
        "list" => {
            let path = str_arg("path")
                .unwrap_or_else(|| core.explorer.root().to_string());
            let entries = core.explorer.list(&path)?;
            serde_json::to_value(&entries)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Navigate to a new root
        "navigate" => {
            let path = str_arg("path").ok_or_else(|| {
                NexusError::InvalidState("explorer.navigate requires path".into())
            })?;
            core.explorer.navigate(&path);
            let state = core.explorer.tree()?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Go up one directory
        "up" => {
            core.explorer.up();
            let state = core.explorer.tree()?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Toggle directory expanded/collapsed
        "toggle" => {
            let path = str_arg("path").ok_or_else(|| {
                NexusError::InvalidState("explorer.toggle requires path".into())
            })?;
            let expanded = core.explorer.toggle(&path);
            let state = core.explorer.tree()?;
            let mut val = serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))?;
            val["toggled"] = serde_json::json!(expanded);
            Ok(val)
        }

        // Toggle hidden files
        "hidden" => {
            let show = core.explorer.toggle_hidden();
            let state = core.explorer.tree()?;
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
            let entries = core.explorer.search(&query)?;
            serde_json::to_value(&entries)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        // Cursor navigation — keyboard-driven file tree browsing
        "cursor_down" => {
            let count = core.explorer.tree()?.entries.len();
            core.explorer.cursor_down(count);
            let state = core.explorer.tree()?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "cursor_up" => {
            core.explorer.cursor_up();
            let state = core.explorer.tree()?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "cursor_toggle" => {
            // Get entry at cursor before toggling
            let pre_state = core.explorer.tree()?;
            let entry = pre_state.entries.get(core.explorer.cursor_index()).cloned();

            if let Some(ref e) = entry {
                if !e.entry.is_dir {
                    // File — open in editor via command_line routing
                    let path = e.entry.path.clone();
                    let mut ed_args = HashMap::new();
                    ed_args.insert("raw".to_string(), serde_json::json!(format!("e {path}")));
                    let _ = dispatch(core, "command_line.execute", &ed_args);
                    // Return current state unchanged
                    let state = core.explorer.tree()?;
                    return serde_json::to_value(&state)
                        .map_err(|e| NexusError::InvalidState(e.to_string()));
                }
            }

            // Directory — toggle expand/collapse
            let state = core.explorer.cursor_toggle()?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "cursor_collapse" => {
            let state = core.explorer.cursor_collapse()?;
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        _ => Err(NexusError::NotFound(format!("unknown explorer action: {action}"))),
    }
}
