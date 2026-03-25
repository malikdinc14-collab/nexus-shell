//! Nexus Shell — Tauri desktop app with embedded engine.
//!
//! This is a thin IPC bridge. All tool-owning logic lives in nexus-engine;
//! commands.rs simply delegates to NexusCore methods.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;

use nexus_core::adapters::{ClaudeAdapter, FsExplorer};
use nexus_core::capability::SystemContext;
use nexus_engine::{NexusCore, NullMux};
use std::sync::Mutex;
use tauri::Manager;

/// Shared application state accessible from Tauri commands.
pub struct AppState {
    pub core: Mutex<NexusCore>,
}

fn main() {
    let ctx = SystemContext::from_login_shell();
    let claude = ClaudeAdapter::new(ctx.clone());
    let fs_explorer = FsExplorer::new();

    let mut core = NexusCore::with_registry(Box::new(NullMux::new()), ctx);
    if let Some(ref mut reg) = core.registry {
        reg.register_chat(Box::new(claude));
        reg.register_explorer(Box::new(fs_explorer));
    }

    tauri::Builder::default()
        .manage(AppState {
            core: Mutex::new(core),
        })
        .invoke_handler(tauri::generate_handler![
            commands::create_workspace,
            commands::stack_op,
            commands::list_tabs,
            commands::get_session,
            commands::read_dir,
            commands::read_file,
            commands::get_cwd,
            commands::get_layout,
            commands::split_pane,
            commands::navigate_pane,
            commands::focus_pane,
            commands::close_pane,
            commands::zoom_pane,
            commands::resize_pane,
            commands::pty_spawn,
            commands::pty_write,
            commands::pty_resize,
            commands::pty_kill,
            commands::agent_send,
            commands::get_keymap,
            commands::get_commands,
            commands::dispatch_command,
        ])
        .setup(|app| {
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
