//! Nexus Shell — Tauri desktop app (thin client).
//!
//! Connects to nexus-daemon via NexusClient. All engine state lives in
//! the daemon. This binary is a pure GUI frontend.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;

use nexus_client::{EventSubscription, NexusClient};
use std::sync::Mutex;

/// Shared application state — holds the daemon client connection.
pub struct AppState {
    pub client: Mutex<NexusClient>,
}

fn main() {
    let client = NexusClient::connect().expect("Failed to connect to nexus daemon");

    tauri::Builder::default()
        .manage(AppState {
            client: Mutex::new(client),
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
            // Bridge daemon events to Tauri frontend via EventSubscription
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                // Subscribe to all events
                let mut sub = match EventSubscription::subscribe(&["*.*"], None) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Event subscription failed: {e}");
                        return;
                    }
                };

                loop {
                    match sub.next_event() {
                        Ok(notif) => {
                            use tauri::Emitter;
                            let tauri_event = match notif.method.as_str() {
                                "pty.output" => "pty-output",
                                "pty.exit" => "pty-exit",
                                s if s.starts_with("agent.") => "agent-output",
                                "layout.changed" => "layout-changed",
                                "stack.changed" => "stack-changed",
                                "editor.file_opened" => "editor-file-opened",
                                _ => continue,
                            };

                            let mut payload = match notif.params.as_object() {
                                Some(m) => m.clone(),
                                None => serde_json::Map::new(),
                            };

                            // For agent events, add the type field
                            if notif.method.starts_with("agent.") {
                                let event_type = notif.method.strip_prefix("agent.").unwrap_or("");
                                payload.insert("type".into(), serde_json::json!(event_type));
                            }

                            let _ = app_handle.emit(tauri_event, &serde_json::Value::Object(payload));
                        }
                        Err(_) => {
                            // Connection lost — try to reconnect
                            std::thread::sleep(std::time::Duration::from_secs(1));
                            sub = match EventSubscription::subscribe(&["*.*"], None) {
                                Ok(s) => s,
                                Err(_) => continue,
                            };
                        }
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error running Nexus Shell");
}
