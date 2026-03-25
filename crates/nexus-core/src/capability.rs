//! Capability traits — the contract between adapters and the engine.
//!
//! Every tool backend (editor, chat, explorer, multiplexer) implements one of
//! these traits. Surfaces never own tools; they delegate through capabilities.

use serde::{Deserialize, Serialize};
use std::sync::mpsc;

use crate::error::NexusError;

// ---------------------------------------------------------------------------
// Base types
// ---------------------------------------------------------------------------

/// The kind of capability an adapter provides.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CapabilityType {
    Multiplexer,
    Editor,
    Chat,
    Explorer,
}

/// System-level context for binary resolution.
///
/// macOS GUI apps inherit a minimal PATH. `from_login_shell()` probes the
/// user's login shell to capture the full PATH, so adapters can find binaries
/// like `tmux`, `nvim`, `yazi`, etc.
#[derive(Debug, Clone)]
pub struct SystemContext {
    pub path: String,
    pub shell: String,
}

impl SystemContext {
    /// Probe the login shell for the full PATH.
    pub fn from_login_shell() -> Self {
        let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/sh".to_string());

        // Run the login shell to emit PATH. This captures .zshrc/.bashrc additions.
        let path = std::process::Command::new(&shell)
            .args(["-l", "-c", "echo $PATH"])
            .output()
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
            .unwrap_or_else(|_| std::env::var("PATH").unwrap_or_default());

        SystemContext { path, shell }
    }

    /// Resolve a binary name to its full path using the captured PATH.
    pub fn resolve_binary(&self, name: &str) -> Option<String> {
        for dir in self.path.split(':') {
            let candidate = std::path::Path::new(dir).join(name);
            if candidate.is_file() {
                return Some(candidate.to_string_lossy().to_string());
            }
        }
        None
    }
}

/// Static manifest describing an adapter.
#[derive(Debug, Clone)]
pub struct AdapterManifest {
    pub name: &'static str,
    pub capability_type: CapabilityType,
    pub priority: u32,
    pub binary: &'static str,
}

// ---------------------------------------------------------------------------
// Base capability trait
// ---------------------------------------------------------------------------

/// Every adapter implements Capability for lifecycle and discovery.
pub trait Capability: Send + Sync {
    /// Return the static manifest for this adapter.
    fn manifest(&self) -> AdapterManifest;

    /// Check whether the adapter's backing binary is available.
    fn is_available(&self) -> bool;
}

// ---------------------------------------------------------------------------
// Chat capability
// ---------------------------------------------------------------------------

/// Events emitted by a chat backend during a conversation turn.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ChatEvent {
    Start { backend: String },
    Text { chunk: String },
    Done { exit_code: i32, full_text: String },
    Error { message: String },
}

/// A chat backend (Claude Code, Aider, etc.).
pub trait ChatCapability: Capability {
    /// Send a message and stream events back through `tx`.
    fn send_message(
        &self,
        message: &str,
        cwd: &str,
        tx: mpsc::Sender<ChatEvent>,
    ) -> Result<(), NexusError>;

    /// Return the shell command to launch this chat backend, if applicable.
    fn get_launch_command(&self) -> Option<String>;
}

// ---------------------------------------------------------------------------
// Editor capability
// ---------------------------------------------------------------------------

/// A headless editor backend (Neovim, Helix, etc.).
pub trait EditorCapability: Capability {
    /// Open a file at the given path, optionally at a line number.
    fn open(&mut self, path: &str, line: Option<u32>) -> Result<(), NexusError>;

    /// Return the path of the currently active buffer.
    fn get_current_buffer(&self) -> Result<String, NexusError>;

    /// Return the full text content of a buffer.
    fn get_buffer_content(&self, buffer: &str) -> Result<String, NexusError>;

    /// Apply a text edit to a buffer.
    fn apply_edit(
        &mut self,
        buffer: &str,
        start_line: u32,
        end_line: u32,
        text: &str,
    ) -> Result<(), NexusError>;

    /// List open tabs/buffers.
    fn get_tabs(&self) -> Result<Vec<String>, NexusError>;

    /// Send an ex-command or equivalent.
    fn send_command(&mut self, command: &str) -> Result<String, NexusError>;

    /// Evaluate a remote expression (Neovim: nvim_eval).
    fn remote_expr(&self, expr: &str) -> Result<String, NexusError>;

    /// Check whether the editor process is still running.
    fn is_alive(&self) -> bool;
}

// ---------------------------------------------------------------------------
// Explorer capability
// ---------------------------------------------------------------------------

/// A single directory entry returned by an explorer backend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirEntry {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub size: u64,
}

/// A file explorer backend (Yazi, lf, etc.).
pub trait ExplorerCapability: Capability {
    /// List entries in a directory.
    fn list_directory(&self, path: &str) -> Result<Vec<DirEntry>, NexusError>;

    /// Return the currently selected entry path, if any.
    fn get_selection(&self) -> Result<Option<String>, NexusError>;

    /// Trigger a named action (open, delete, rename, etc.).
    fn trigger_action(&mut self, action: &str, path: &str) -> Result<(), NexusError>;

    /// Return the shell command to launch this explorer, if applicable.
    fn get_launch_command(&self) -> Option<String>;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn system_context_from_login_shell_returns_non_empty_path() {
        let ctx = SystemContext::from_login_shell();
        assert!(!ctx.path.is_empty(), "PATH should not be empty");
        assert!(!ctx.shell.is_empty(), "shell should not be empty");
    }

    #[test]
    fn system_context_resolve_binary_finds_ls() {
        let ctx = SystemContext::from_login_shell();
        let resolved = ctx.resolve_binary("ls");
        assert!(resolved.is_some(), "ls should be resolvable");
        assert!(resolved.unwrap().contains("ls"));
    }

    #[test]
    fn system_context_resolve_binary_returns_none_for_nonexistent() {
        let ctx = SystemContext::from_login_shell();
        assert!(ctx.resolve_binary("definitely_not_a_real_binary_xyz").is_none());
    }

    #[test]
    fn adapter_manifest_fields() {
        let m = AdapterManifest {
            name: "test",
            capability_type: CapabilityType::Chat,
            priority: 100,
            binary: "test-bin",
        };
        assert_eq!(m.name, "test");
        assert_eq!(m.capability_type, CapabilityType::Chat);
        assert_eq!(m.priority, 100);
    }

    #[test]
    fn capability_type_variants() {
        let types = [
            CapabilityType::Multiplexer,
            CapabilityType::Editor,
            CapabilityType::Chat,
            CapabilityType::Explorer,
        ];
        for (i, a) in types.iter().enumerate() {
            for (j, b) in types.iter().enumerate() {
                if i == j {
                    assert_eq!(a, b);
                } else {
                    assert_ne!(a, b);
                }
            }
        }
    }
}
