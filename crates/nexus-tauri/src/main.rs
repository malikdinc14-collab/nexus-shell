//! Nexus Shell — Tauri desktop app with embedded engine.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;

use nexus_engine::{NexusCore, NullMux};
use std::sync::Mutex;
use tauri::Manager;

/// Shared application state accessible from Tauri commands.
pub struct AppState {
    pub core: Mutex<NexusCore>,
}

fn main() {
    // NexusCore with NullMux for now — TauriMux will replace this
    let core = NexusCore::new(Box::new(NullMux::new()));

    tauri::Builder::default()
        .manage(AppState {
            core: Mutex::new(core),
        })
        .invoke_handler(tauri::generate_handler![
            commands::create_workspace,
            commands::stack_op,
            commands::list_tabs,
            commands::get_session,
        ])
        .setup(|app| {
            // Initialize workspace on startup
            let state = app.state::<AppState>();
            let mut core = state.core.lock().unwrap();
            let cwd = std::env::current_dir()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default();
            core.create_workspace("nexus", &cwd);
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error running Nexus Shell");
}
