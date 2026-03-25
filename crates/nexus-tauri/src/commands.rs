//! Tauri commands — IPC bridge between frontend and nexus-daemon.
//!
//! Each command locks the NexusClient and sends a JSON-RPC request.

use crate::AppState;
use serde::Serialize;
use std::collections::HashMap;
use std::path::PathBuf;
use tauri::State;

// -- Engine commands (delegated to daemon) -----------------------------------

#[tauri::command]
pub fn create_workspace(
    state: State<AppState>,
    name: String,
    cwd: String,
) -> Result<String, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    let result = client.session_create(&name, &cwd).map_err(|e| e.to_string())?;
    Ok(result.get("session_id").and_then(|v| v.as_str()).unwrap_or("").to_string())
}

#[tauri::command]
pub fn stack_op(
    state: State<AppState>,
    op: String,
    payload: HashMap<String, String>,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.stack_op(&op, &payload).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn list_tabs(
    state: State<AppState>,
    identity: String,
) -> Result<Vec<serde_json::Value>, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    let result = client.request(
        "stack.list",
        serde_json::json!({"identity": identity}),
    ).map_err(|e| e.to_string())?;
    match result.as_array() {
        Some(arr) => Ok(arr.clone()),
        None => Ok(Vec::new()),
    }
}

#[tauri::command]
pub fn get_session(state: State<AppState>) -> Result<Option<String>, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    let result = client.session_info().map_err(|e| e.to_string())?;
    Ok(result.get("name").and_then(|v| v.as_str()).map(String::from))
}

// -- Filesystem commands (local, not through daemon) -------------------------

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
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.layout().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn split_pane(
    state: State<AppState>,
    direction: String,
    pane_type: String,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.request("pane.split", serde_json::json!({
        "direction": direction,
        "pane_type": pane_type,
    })).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn navigate_pane(
    state: State<AppState>,
    direction: String,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.navigate(&direction).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn focus_pane(
    state: State<AppState>,
    pane_id: String,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.focus(&pane_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn close_pane(
    state: State<AppState>,
    pane_id: String,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.close_pane(&pane_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn zoom_pane(state: State<AppState>) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.zoom().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn resize_pane(
    state: State<AppState>,
    pane_id: String,
    ratio: f64,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.resize(&pane_id, ratio).map_err(|e| e.to_string())
}

// -- PTY commands ------------------------------------------------------------

#[tauri::command]
pub fn pty_spawn(
    state: State<AppState>,
    pane_id: String,
    cwd: Option<String>,
) -> Result<(), String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.pty_spawn(&pane_id, cwd.as_deref()).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn pty_write(state: State<AppState>, pane_id: String, data: String) -> Result<(), String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.pty_write(&pane_id, data.as_bytes()).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn pty_resize(
    state: State<AppState>,
    pane_id: String,
    cols: u16,
    rows: u16,
) -> Result<(), String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.pty_resize(&pane_id, cols, rows).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn pty_kill(state: State<AppState>, pane_id: String) -> Result<(), String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.pty_kill(&pane_id).map_err(|e| e.to_string())
}

// -- Agent commands ----------------------------------------------------------

#[tauri::command]
pub fn agent_send(
    state: State<AppState>,
    pane_id: String,
    message: String,
    backend: Option<String>,
    cwd: Option<String>,
) -> Result<(), String> {
    let _ = backend; // TODO: wire backend selection
    let cwd = cwd.unwrap_or_else(|| {
        std::env::current_dir()
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|_| "/tmp".into())
    });
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.chat_send(&pane_id, &message, Some(&cwd)).map_err(|e| e.to_string())
}

// -- Keymap & dispatch commands ----------------------------------------------

#[tauri::command]
pub fn get_keymap(state: State<AppState>) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.keymap().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_commands(state: State<AppState>) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.commands().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn dispatch_command(
    state: State<AppState>,
    command: String,
    args: Option<HashMap<String, serde_json::Value>>,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    let params = match args {
        Some(map) => serde_json::to_value(map).unwrap_or(serde_json::Value::Null),
        None => serde_json::Value::Null,
    };
    client.request(&command, params).map_err(|e| e.to_string())
}
