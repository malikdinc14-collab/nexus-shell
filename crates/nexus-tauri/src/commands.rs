//! Tauri commands — IPC bridge between frontend and NexusCore.

use crate::AppState;
use nexus_engine::{Direction, Nav, PaneType};
use serde::Serialize;
use std::collections::HashMap;
use std::path::PathBuf;
use tauri::State;

// -- Engine commands ---------------------------------------------------------

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

// -- Filesystem commands -----------------------------------------------------

#[derive(Serialize)]
pub struct DirEntry {
    name: String,
    path: String,
    is_dir: bool,
}

#[tauri::command]
pub fn read_dir(path: String) -> Result<Vec<DirEntry>, String> {
    let dir = PathBuf::from(&path);
    if !dir.is_dir() {
        return Err(format!("Not a directory: {path}"));
    }

    let mut entries: Vec<DirEntry> = std::fs::read_dir(&dir)
        .map_err(|e| e.to_string())?
        .filter_map(|e| e.ok())
        .filter(|e| {
            let name = e.file_name().to_string_lossy().to_string();
            !name.starts_with('.') && name != "target" && name != "node_modules"
                && name != "__pycache__"
        })
        .map(|e| {
            let is_dir = e.file_type().map(|t| t.is_dir()).unwrap_or(false);
            DirEntry {
                name: e.file_name().to_string_lossy().to_string(),
                path: e.path().to_string_lossy().to_string(),
                is_dir,
            }
        })
        .collect();

    // Dirs first, then files, alphabetical within each
    entries.sort_by(|a, b| {
        b.is_dir.cmp(&a.is_dir).then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
    });

    Ok(entries)
}

#[tauri::command]
pub fn read_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(&path).map_err(|e| format!("{path}: {e}"))
}

#[tauri::command]
pub fn get_cwd() -> Result<String, String> {
    std::env::current_dir()
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|e| e.to_string())
}

// -- Layout commands ---------------------------------------------------------

#[tauri::command]
pub fn get_layout(state: State<AppState>) -> Result<serde_json::Value, String> {
    let core = state.core.lock().map_err(|e| e.to_string())?;
    Ok(core.layout.to_json())
}

#[tauri::command]
pub fn split_pane(
    state: State<AppState>,
    direction: String,
    pane_type: String,
) -> Result<serde_json::Value, String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    let dir = match direction.as_str() {
        "horizontal" | "h" => Direction::Horizontal,
        _ => Direction::Vertical,
    };
    let pt = PaneType::from_str(&pane_type);
    let _new_id = core.layout.split_focused(dir, pt);
    Ok(core.layout.to_json())
}

#[tauri::command]
pub fn navigate_pane(
    state: State<AppState>,
    direction: String,
) -> Result<serde_json::Value, String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    let nav = match direction.as_str() {
        "left" | "h" => Nav::Left,
        "down" | "j" => Nav::Down,
        "up" | "k" => Nav::Up,
        _ => Nav::Right,
    };
    core.layout.navigate(nav);
    Ok(core.layout.to_json())
}

#[tauri::command]
pub fn focus_pane(
    state: State<AppState>,
    pane_id: String,
) -> Result<serde_json::Value, String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    core.layout.set_focus(&pane_id);
    Ok(core.layout.to_json())
}

#[tauri::command]
pub fn close_pane(
    state: State<AppState>,
    pane_id: String,
) -> Result<serde_json::Value, String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    core.layout.close_pane(&pane_id);
    Ok(core.layout.to_json())
}

#[tauri::command]
pub fn zoom_pane(state: State<AppState>) -> Result<serde_json::Value, String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    core.layout.toggle_zoom();
    Ok(core.layout.to_json())
}

#[tauri::command]
pub fn resize_pane(
    state: State<AppState>,
    pane_id: String,
    ratio: f64,
) -> Result<serde_json::Value, String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    core.layout.set_ratio(&pane_id, ratio);
    Ok(core.layout.to_json())
}

// -- PTY commands (delegated to engine) --------------------------------------

#[tauri::command]
pub fn pty_spawn(
    state: State<AppState>,
    pane_id: String,
    cwd: Option<String>,
) -> Result<(), String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    core.pty_spawn(&pane_id, cwd.as_deref())
}

#[tauri::command]
pub fn pty_write(state: State<AppState>, pane_id: String, data: String) -> Result<(), String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    core.pty_write(&pane_id, &data)
}

#[tauri::command]
pub fn pty_resize(
    state: State<AppState>,
    pane_id: String,
    cols: u16,
    rows: u16,
) -> Result<(), String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    core.pty_resize(&pane_id, cols, rows)
}

#[tauri::command]
pub fn pty_kill(state: State<AppState>, pane_id: String) -> Result<(), String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    core.pty_kill(&pane_id)
}

// -- Agent commands (delegated to engine) ------------------------------------

#[tauri::command]
pub fn agent_send(
    state: State<AppState>,
    pane_id: String,
    message: String,
    backend: Option<String>,
    cwd: Option<String>,
) -> Result<(), String> {
    let _ = backend; // TODO: wire backend selection through registry
    let cwd = cwd.unwrap_or_else(|| {
        std::env::current_dir()
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|_| "/tmp".into())
    });
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    core.chat_send(&pane_id, &message, &cwd)
}

// -- Keymap & dispatch commands ----------------------------------------------

#[tauri::command]
pub fn get_keymap(state: State<AppState>) -> Result<serde_json::Value, String> {
    let core = state.core.lock().map_err(|e| e.to_string())?;
    serde_json::to_value(core.get_keymap()).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_commands(state: State<AppState>) -> Result<serde_json::Value, String> {
    let core = state.core.lock().map_err(|e| e.to_string())?;
    serde_json::to_value(core.get_commands()).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn dispatch_command(
    state: State<AppState>,
    command: String,
    args: Option<HashMap<String, serde_json::Value>>,
) -> Result<serde_json::Value, String> {
    let mut core = state.core.lock().map_err(|e| e.to_string())?;
    let args = args.unwrap_or_default();
    nexus_engine::dispatch(&mut core, &command, &args).map_err(|e| e.to_string())
}
