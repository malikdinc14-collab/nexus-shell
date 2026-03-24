//! Tauri commands — IPC bridge between frontend and NexusCore.

use crate::AppState;
use std::collections::HashMap;
use tauri::State;

#[tauri::command]
pub fn create_workspace(
    state: State<AppState>,
    name: String,
    cwd: String,
) -> Result<String, String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    let session = core.create_workspace(&name, &cwd);
    Ok(session)
}

#[tauri::command]
pub fn stack_op(
    state: State<AppState>,
    op: String,
    payload: HashMap<String, String>,
) -> Result<serde_json::Value, String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    let result = core.handle_stack_op(&op, &payload);
    let mut map = serde_json::Map::new();
    map.insert("status".into(), serde_json::Value::String(result.status));
    for (k, v) in result.data {
        map.insert(k, v);
    }
    Ok(serde_json::Value::Object(map))
}

#[tauri::command]
pub fn list_tabs(
    state: State<AppState>,
    identity: String,
) -> Result<Vec<serde_json::Value>, String> {
    let core = state.core.lock().map_err(|e| e.to_string())?;
    match core.stacks.get_by_identity(&identity) {
        Some((_, stack)) => {
            let tabs: Vec<serde_json::Value> = stack
                .tabs
                .iter()
                .map(|t| {
                    serde_json::json!({
                        "id": t.pane_handle.as_deref().unwrap_or(&t.id),
                        "name": t.name,
                        "active": t.is_active,
                    })
                })
                .collect();
            Ok(tabs)
        }
        None => Ok(Vec::new()),
    }
}

#[tauri::command]
pub fn get_session(state: State<AppState>) -> Result<Option<String>, String> {
    let core = state.core.lock().map_err(|e| e.to_string())?;
    Ok(core.session().map(|s| s.to_string()))
}
