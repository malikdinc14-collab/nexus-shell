use std::collections::HashMap;
use nexus_core::NexusError;
use crate::core::NexusCore;
use super::resolve_active_module;

// ---------------------------------------------------------------------------
// chat.*
// ---------------------------------------------------------------------------

pub fn handle_chat(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "send" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("chat.send requires pane_id".into())
            })?;
            let message = str_arg("message").ok_or_else(|| {
                NexusError::InvalidState("chat.send requires message".into())
            })?;
            let cwd = str_arg("cwd").unwrap_or_else(|| "/tmp".into());

            // Also delegate to legacy chat_send if registry has a chat adapter
            if core.registry.is_some() {
                let _ = core.chat_send(&pane_id, &message, &cwd);
            }

            let conv = core.chat.send(&pane_id, &message, &cwd)?;
            serde_json::to_value(&conv)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "history" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("chat.history requires pane_id".into())
            })?;
            match core.chat.history(&pane_id) {
                Some(conv) => serde_json::to_value(conv)
                    .map_err(|e| NexusError::InvalidState(e.to_string())),
                None => Ok(serde_json::json!({"messages": []})),
            }
        }
        "clear" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("chat.clear requires pane_id".into())
            })?;
            let cleared = core.chat.clear(&pane_id);
            Ok(serde_json::json!({"cleared": cleared}))
        }
        "state" => {
            let state = core.chat.state();
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown chat action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// browser.*
// ---------------------------------------------------------------------------

pub fn handle_browser(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "open" => {
            let url = str_arg("url").unwrap_or_else(|| "https://google.com".into());
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());

            // 1. Create session in engine
            let session = core.browser.open(&pane_id, &url)?;

            // 2. Ensure the pane has a Browser tab
            let (sid, stack) = core.stacks.get_or_create_by_identity(&pane_id, None);
            let sid = sid.clone();

            // If active tab isn't Browser, push or switch to it
            let has_browser = stack.tabs.iter().any(|t| t.name == "Browser");
            if !has_browser {
                let tab = crate::stack::Tab::new("Browser")
                    .with_status(crate::stack::TabStatus::Visible, true);
                core.stacks.push(&sid, tab);
            } else {
                // Find index and switch
                let idx = stack.tabs.iter().position(|t| t.name == "Browser").unwrap();
                let mut switch_args = HashMap::new();
                switch_args.insert("identity".into(), pane_id.clone());
                switch_args.insert("index".into(), idx.to_string());
                core.handle_stack_op("switch", &switch_args);
            }

            core.mark_dirty();
            serde_json::to_value(&session)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "navigate" => {
            let pane_id = str_arg("pane_id")
                .unwrap_or_else(|| core.layout.focused.clone());
            let url = str_arg("url").ok_or_else(|| {
                NexusError::InvalidState("browser.navigate requires url".into())
            })?;

            core.browser.navigate(&pane_id, &url)?;
            core.mark_dirty();
            Ok(serde_json::json!({"status": "ok"}))
        }
        "state" => {
            let state = core.browser.state();
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown browser action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// terminal.* 
// ---------------------------------------------------------------------------

pub fn handle_terminal(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "state" => {
            let state = core.terminal.state();
            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "info" => {
            let info = core.terminal.info();
            serde_json::to_value(&info)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "session" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("terminal.session requires pane_id".into())
            })?;
            match core.terminal.session(&pane_id) {
                Some(s) => serde_json::to_value(s)
                    .map_err(|e| NexusError::InvalidState(e.to_string())),
                None => Err(NexusError::NotFound(format!("no terminal session: {pane_id}"))),
            }
        }
        "register" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("terminal.register requires pane_id".into())
            })?;
            let cwd = str_arg("cwd");
            let s = core.terminal.register_session(&pane_id, cwd.as_deref());
            serde_json::to_value(&s)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        "remove" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("terminal.remove requires pane_id".into())
            })?;
            core.terminal.remove_sessions(&pane_id);
            Ok(serde_json::json!({"status": "ok"}))
        }
        _ => Err(NexusError::NotFound(format!("unknown terminal action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// pty.*
// ---------------------------------------------------------------------------

pub fn handle_pty(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "spawn" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.spawn requires pane_id".into())
            })?;
            let cwd = str_arg("cwd");
            let command = str_arg("command");

            if let Some(cmd) = command {
                let cwd_str = cwd.as_deref().unwrap_or("/tmp");
                core.pty_spawn_cmd(&pane_id, cwd_str, &cmd, &[])?;
            } else {
                core.pty_spawn(&pane_id, cwd.as_deref())?;
            }
            Ok(serde_json::json!({ "pane_id": pane_id, "status": "ok" }))
        }
        "input" | "write" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.write requires pane_id".into())
            })?;
            let raw = str_arg("data").ok_or_else(|| {
                NexusError::InvalidState("pty.write requires data".into())
            })?;
            // Client may base64-encode binary data; try decoding first.
            let decoded = {
                use base64::Engine;
                base64::engine::general_purpose::STANDARD.decode(&raw).ok()
            };
            let text = match &decoded {
                Some(bytes) => std::str::from_utf8(bytes).unwrap_or(&raw),
                None => &raw,
            };
            core.pty_write(&pane_id, text)?;
            Ok(serde_json::json!({"status": "ok"}))
        }
        "resize" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.resize requires pane_id".into())
            })?;
            let cols = args.get("cols").and_then(|v| v.as_u64()).unwrap_or(80) as u16;
            let rows = args.get("rows").and_then(|v| v.as_u64()).unwrap_or(24) as u16;
            core.pty_resize(&pane_id, cols, rows)?;
            Ok(serde_json::json!({"status": "ok"}))
        }
        "kill" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.kill requires pane_id".into())
            })?;
            core.pty_kill(&pane_id)?;
            Ok(serde_json::json!({"status": "ok"}))
        }
        _ => Err(NexusError::NotFound(format!("unknown pty action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// session.*
// ---------------------------------------------------------------------------

pub fn handle_session(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "save" => {
            let name = str_arg("name").unwrap_or_else(|| "default".into());
            let session_dir = crate::persistence::session_dir(&name);
            let save = core.snapshot();
            crate::persistence::save_workspace(&session_dir, &save)?;
            let path = session_dir.to_string_lossy().to_string();
            Ok(serde_json::json!({ "path": path }))
        }
        "load" => {
            let name = str_arg("name").unwrap_or_else(|| "default".into());
            let session_dir = crate::persistence::session_dir(&name);
            let save = crate::persistence::load_workspace(&session_dir)
                .map_err(|e| NexusError::NotFound(format!("session '{name}' not found: {e}")))?;
            core.layout = save.layout;
            core.stacks = save.stacks;
            core.mark_dirty();
            Ok(serde_json::json!({ "status": "ok" }))
        }
        "list" => {
            let sessions = core.session_list();
            Ok(serde_json::Value::Array(sessions))
        }
        "info" => {
            let name = core.session().unwrap_or("unnamed").to_string();
            Ok(serde_json::json!({ "name": name, "cwd": core.cwd() }))
        }
        _ => Err(NexusError::NotFound(format!("unknown session action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// keymap.*
// ---------------------------------------------------------------------------

pub fn handle_keymap(
    core: &NexusCore,
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "get" => serde_json::to_value(core.get_keymap())
            .map_err(|e| NexusError::InvalidState(e.to_string())),
        _ => Err(NexusError::NotFound(format!("unknown keymap action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// commands.*
// ---------------------------------------------------------------------------

pub fn handle_commands(
    core: &NexusCore,
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "list" => serde_json::to_value(core.get_commands())
            .map_err(|e| NexusError::InvalidState(e.to_string())),
        _ => Err(NexusError::NotFound(format!("unknown commands action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// capabilities.*
// ---------------------------------------------------------------------------

pub fn handle_capabilities(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "list" => {
            let type_filter = args.get("type").and_then(|v| v.as_str());
            Ok(core.capabilities_list(type_filter))
        }
        _ => Err(NexusError::NotFound(format!("unknown capabilities action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// nexus.*
// ---------------------------------------------------------------------------

pub fn handle_nexus(
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "hello" => Ok(serde_json::json!({
            "version": env!("CARGO_PKG_VERSION"),
            "protocol": 1,
        })),
        _ => Err(NexusError::NotFound(format!("unknown nexus action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// command_line.*
// ---------------------------------------------------------------------------

pub fn handle_command_line(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "execute" => {
            let raw = args
                .get("raw")
                .and_then(|v| v.as_str())
                .ok_or_else(|| NexusError::InvalidState("command_line.execute requires raw".into()))?;

            let parts: Vec<&str> = raw.split_whitespace().collect();
            if parts.is_empty() {
                return Ok(serde_json::json!({"status": "empty"}));
            }

            match parts[0] {
                "q" => super::dispatch(core, "pane.close", &HashMap::new()),
                "wq" => {
                    let _ = super::dispatch(core, "session.save", args);
                    super::dispatch(core, "pane.close", &HashMap::new())
                }
                "e" | "edit" if parts.len() >= 2 => {
                    let path = parts[1..].join(" ");
                    let target_pane = super::resolve_editor_pane(core);

                    let mut ed_args = HashMap::new();
                    ed_args.insert("path".to_string(), serde_json::json!(path));
                    ed_args.insert("pane_id".to_string(), serde_json::json!(&target_pane));
                    let result = super::dispatch(core, "editor.open", &ed_args)?;

                    let mut set_args = HashMap::new();
                    set_args.insert("identity".to_string(), serde_json::json!(&target_pane));
                    set_args.insert("name".to_string(), serde_json::json!("Editor"));
                    super::dispatch(core, "stack.set_content", &set_args)?;

                    Ok(result)
                }
                // :md <path> or :markdown <path> — open in RichText
                "md" | "markdown" if parts.len() >= 2 => {
                    let path = parts[1..].join(" ");
                    let focused = core.layout.focused.clone();

                    let mut md_args = HashMap::new();
                    md_args.insert("path".to_string(), serde_json::json!(path));
                    md_args.insert("pane_id".to_string(), serde_json::json!(&focused));
                    let result = super::dispatch(core, "markdown.open", &md_args)?;

                    Ok(result)
                }
                _ => Err(NexusError::NotFound(format!("unknown command: {}", parts[0]))),
            }
        }
        _ => Err(NexusError::NotFound(format!("unknown command_line action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// info.*
// ---------------------------------------------------------------------------

pub fn handle_info(
    core: &NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "system" => {
            let data = crate::info::collect(core);
            serde_json::to_value(&data).map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown info action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// content.*
// ---------------------------------------------------------------------------

pub fn handle_content(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    use crate::content_tabs::TabProvider;

    let pane_id = args
        .get("pane_id")
        .and_then(|v| v.as_str())
        .map(String::from)
        .unwrap_or_else(|| core.layout.focused.clone());

    let module = resolve_active_module(core, &pane_id)
        .unwrap_or_default();

    match action {
        "tabs" => {
            let state = match module.as_str() {
                "Editor" => core.editor.content_tabs(&pane_id),
                "Terminal" => core.terminal.content_tabs(&pane_id),
                "Chat" => core.chat.content_tabs(&pane_id),
                _ => None,
            };
            match state {
                Some(s) => serde_json::to_value(&s)
                    .map_err(|e| NexusError::InvalidState(e.to_string())),
                None => Ok(serde_json::json!(null)),
            }
        }

        "switch" => {
            let index = args.get("index")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| NexusError::InvalidState("content.switch requires index".into()))?
                as usize;

            let state = match module.as_str() {
                "Editor" => core.editor.switch_content_tab(&pane_id, index),
                "Terminal" => core.terminal.switch_content_tab(&pane_id, index),
                "Chat" => core.chat.switch_content_tab(&pane_id, index),
                _ => Err(NexusError::InvalidState(format!("module {module} has no content tabs"))),
            }?;

            let mut payload = HashMap::new();
            payload.insert("pane_id".to_string(), serde_json::json!(pane_id));
            payload.insert("state".to_string(), serde_json::to_value(&state).unwrap_or_default());
            core.publish("content.changed", payload);

            serde_json::to_value(&state)
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }

        "close" => {
            let index = args.get("index")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| NexusError::InvalidState("content.close requires index".into()))?
                as usize;

            let result = match module.as_str() {
                "Editor" => core.editor.close_content_tab(&pane_id, index),
                "Terminal" => core.terminal.close_content_tab(&pane_id, index),
                "Chat" => core.chat.close_content_tab(&pane_id, index),
                _ => Err(NexusError::InvalidState(format!("module {module} has no content tabs"))),
            }?;

            let mut payload = HashMap::new();
            payload.insert("pane_id".to_string(), serde_json::json!(pane_id));
            core.publish("content.changed", payload);

            match result {
                Some(s) => serde_json::to_value(&s)
                    .map_err(|e| NexusError::InvalidState(e.to_string())),
                None => Ok(serde_json::json!(null)),
            }
        }

        _ => Err(NexusError::NotFound(format!("unknown content action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// menu.*
// ---------------------------------------------------------------------------

pub fn handle_menu(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "get" => {
            let context = str_arg("context").unwrap_or_else(|| "home".into());
            let list = core.menu.get(&context);
            serde_json::to_value(&list).map_err(|e| NexusError::Protocol(e.to_string()))
        }
        "navigate" => {
            let context = str_arg("context").ok_or_else(|| {
                NexusError::InvalidState("menu.navigate requires context".into())
            })?;
            let list = core.menu.navigate(&context);
            serde_json::to_value(&list).map_err(|e| NexusError::Protocol(e.to_string()))
        }
        "back" => {
            let list = core.menu.back();
            serde_json::to_value(&list).map_err(|e| NexusError::Protocol(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown menu action: {action}"))),
    }
}

// ---------------------------------------------------------------------------
// workspace.*
// ---------------------------------------------------------------------------

pub fn handle_workspace(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        // workspace.init — scaffold .nexus/ in the given (or current) directory
        "init" => {
            let cwd = str_arg("cwd")
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|| std::path::PathBuf::from(core.cwd()));

            let nexus_dir = cwd.join(".nexus");
            std::fs::create_dir_all(&nexus_dir)
                .map_err(|e| NexusError::Io(e.to_string()))?;

            // config.yaml
            let config_path = nexus_dir.join("config.yaml");
            if !config_path.exists() {
                let dir_name = cwd.file_name()
                    .map(|n| n.to_string_lossy().to_string())
                    .unwrap_or_else(|| "workspace".into());
                std::fs::write(&config_path, format!(
                    "# Nexus workspace config\nworkspace: {dir_name}\n# shell: /bin/zsh\n"
                )).map_err(|e| NexusError::Io(e.to_string()))?;
            }

            // keymap.conf
            let keymap_path = nexus_dir.join("keymap.conf");
            if !keymap_path.exists() {
                std::fs::write(&keymap_path,
                    "# Workspace keybindings (overrides global)\n# Alt+x = some.action\n"
                ).map_err(|e| NexusError::Io(e.to_string()))?;
            }

            // menu/ directory
            let menu_dir = nexus_dir.join("menu");
            std::fs::create_dir_all(&menu_dir)
                .map_err(|e| NexusError::Io(e.to_string()))?;

            Ok(serde_json::json!({
                "path": nexus_dir.to_string_lossy(),
                "files": [
                    config_path.to_string_lossy(),
                    keymap_path.to_string_lossy(),
                ],
            }))
        }

        // workspace.status — does .nexus/ exist in cwd?
        "status" => {
            let cwd = str_arg("cwd")
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|| std::path::PathBuf::from(core.cwd()));
            let nexus_dir = cwd.join(".nexus");
            let exists = nexus_dir.exists();
            let config_path = nexus_dir.join("config.yaml");

            let name = if config_path.exists() {
                std::fs::read_to_string(&config_path).ok()
                    .and_then(|s| {
                        s.lines()
                         .find(|l| l.starts_with("workspace:"))
                         .map(|l| l.trim_start_matches("workspace:").trim().to_string())
                    })
            } else {
                None
            };

            Ok(serde_json::json!({
                "initialized": exists,
                "path": nexus_dir.to_string_lossy(),
                "name": name,
                "cwd": cwd.to_string_lossy(),
            }))
        }

        _ => Err(NexusError::NotFound(format!("unknown workspace action: {action}"))),
    }
}
