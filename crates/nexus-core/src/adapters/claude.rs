//! ClaudeAdapter — ChatCapability backed by the `claude` CLI.
//!
//! Spawns `claude -p <message> --output-format stream-json` in a background
//! thread, parses NDJSON output, and pushes ChatEvent variants to the channel.

use std::io::BufRead;
use std::sync::mpsc;

use crate::capability::{
    AdapterManifest, Capability, CapabilityType, ChatCapability, ChatEvent, SystemContext,
};
use crate::error::NexusError;

pub struct ClaudeAdapter {
    manifest: AdapterManifest,
    ctx: SystemContext,
}

impl ClaudeAdapter {
    pub fn new(ctx: SystemContext) -> Self {
        Self {
            manifest: AdapterManifest {
                name: "claude",
                capability_type: CapabilityType::Chat,
                priority: 100,
                binary: "claude",
            },
            ctx,
        }
    }
}

impl Capability for ClaudeAdapter {
    fn manifest(&self) -> &AdapterManifest {
        &self.manifest
    }

    fn is_available(&self) -> bool {
        self.ctx.resolve_binary("claude").is_some()
    }
}

impl ChatCapability for ClaudeAdapter {
    fn send_message(
        &self,
        message: &str,
        cwd: &str,
        tx: mpsc::Sender<ChatEvent>,
    ) -> Result<(), NexusError> {
        let resolved = self
            .ctx
            .resolve_binary("claude")
            .ok_or_else(|| NexusError::NotFound("claude binary not found".into()))?;

        let path_env = self.ctx.path.clone();
        let message = message.to_string();
        let cwd = cwd.to_string();

        std::thread::spawn(move || {
            let _ = tx.send(ChatEvent::Start {
                backend: "claude".into(),
            });

            let child = std::process::Command::new(&resolved)
                .args(["-p", &message, "--output-format", "stream-json"])
                .env("PATH", &path_env)
                .current_dir(&cwd)
                .stdout(std::process::Stdio::piped())
                .stderr(std::process::Stdio::piped())
                .stdin(std::process::Stdio::null())
                .spawn();

            let mut child = match child {
                Ok(c) => c,
                Err(e) => {
                    let _ = tx.send(ChatEvent::Error {
                        message: format!("failed to spawn claude: {e}"),
                    });
                    return;
                }
            };

            let stdout = match child.stdout.take() {
                Some(s) => s,
                None => {
                    let _ = tx.send(ChatEvent::Error {
                        message: "no stdout from claude process".into(),
                    });
                    return;
                }
            };

            let reader = std::io::BufReader::new(stdout);
            let mut full_text = String::new();

            for line in reader.lines() {
                let line = match line {
                    Ok(l) => l,
                    Err(e) => {
                        let _ = tx.send(ChatEvent::Error {
                            message: format!("read error: {e}"),
                        });
                        break;
                    }
                };

                if line.trim().is_empty() {
                    continue;
                }

                let chunk = extract_text_from_ndjson(&line);
                if !chunk.is_empty() {
                    full_text.push_str(&chunk);
                    let _ = tx.send(ChatEvent::Text {
                        chunk: chunk.clone(),
                    });
                }
            }

            let exit_code = child
                .wait()
                .map(|s| s.code().unwrap_or(-1))
                .unwrap_or(-1);

            let _ = tx.send(ChatEvent::Done {
                exit_code,
                full_text,
            });
        });

        Ok(())
    }

    fn get_launch_command(&self) -> Option<String> {
        self.ctx.resolve_binary("claude")
    }
}

/// Extract displayable text from a single NDJSON line emitted by
/// `claude --output-format stream-json`.
fn extract_text_from_ndjson(line: &str) -> String {
    let json: serde_json::Value = match serde_json::from_str(line) {
        Ok(v) => v,
        Err(_) => return line.to_string(), // Plain text fallback
    };

    let event_type = json.get("type").and_then(|t| t.as_str()).unwrap_or("");

    match event_type {
        "content_block_delta" => json
            .get("delta")
            .and_then(|d| d.get("text"))
            .and_then(|t| t.as_str())
            .unwrap_or("")
            .to_string(),

        "assistant" => json
            .get("message")
            .and_then(|m| m.get("content"))
            .and_then(|c| c.as_array())
            .map(|blocks| {
                blocks
                    .iter()
                    .filter_map(|b| {
                        if b.get("type").and_then(|t| t.as_str()) == Some("text") {
                            b.get("text").and_then(|t| t.as_str())
                        } else {
                            None
                        }
                    })
                    .collect::<Vec<_>>()
                    .join("")
            })
            .unwrap_or_default(),

        "result" => json
            .get("result")
            .and_then(|r| r.as_str())
            .unwrap_or("")
            .to_string(),

        _ => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capability::Capability;

    #[test]
    fn claude_adapter_manifest() {
        let ctx = SystemContext::from_login_shell();
        let adapter = ClaudeAdapter::new(ctx);
        let m = adapter.manifest();
        assert_eq!(m.name, "claude");
        assert_eq!(m.capability_type, CapabilityType::Chat);
        assert_eq!(m.binary, "claude");
    }

    #[test]
    fn claude_adapter_is_send_sync() {
        fn assert_send_sync<T: Send + Sync>() {}
        assert_send_sync::<ClaudeAdapter>();
    }

    #[test]
    fn claude_adapter_get_launch_command() {
        let ctx = SystemContext::from_login_shell();
        let adapter = ClaudeAdapter::new(ctx);
        let cmd = adapter.get_launch_command();
        // Only assert if claude is installed on this machine
        if adapter.is_available() {
            assert!(cmd.is_some());
            assert!(cmd.unwrap().contains("claude"));
        }
    }

    #[test]
    fn claude_adapter_send_message_returns_error_if_binary_missing() {
        let ctx = SystemContext {
            path: "/nonexistent".into(),
            shell: "/bin/sh".into(),
        };
        let adapter = ClaudeAdapter::new(ctx);
        let (tx, _rx) = std::sync::mpsc::channel();
        let result = adapter.send_message("hello", "/tmp", tx);
        assert!(result.is_err());
    }

    #[test]
    fn extract_text_content_block_delta() {
        let line = r#"{"type":"content_block_delta","delta":{"text":"hello"}}"#;
        assert_eq!(extract_text_from_ndjson(line), "hello");
    }

    #[test]
    fn extract_text_assistant() {
        let line = r#"{"type":"assistant","message":{"content":[{"type":"text","text":"world"}]}}"#;
        assert_eq!(extract_text_from_ndjson(line), "world");
    }

    #[test]
    fn extract_text_result() {
        let line = r#"{"type":"result","result":"done"}"#;
        assert_eq!(extract_text_from_ndjson(line), "done");
    }

    #[test]
    fn extract_text_plain_fallback() {
        let line = "just plain text";
        assert_eq!(extract_text_from_ndjson(line), "just plain text");
    }

    #[test]
    fn extract_text_unknown_type_returns_empty() {
        let line = r#"{"type":"ping"}"#;
        assert_eq!(extract_text_from_ndjson(line), "");
    }
}
