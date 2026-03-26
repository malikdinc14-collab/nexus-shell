//! Capability traits — the contract between adapters and the engine.
//!
//! Every tool backend (editor, chat, explorer, multiplexer) implements one of
//! these traits. Surfaces never own tools; they delegate through capabilities.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
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
    Browser,
    RichText,
    HUD,
}

/// System-level context for binary resolution.
///
/// macOS GUI apps inherit a minimal PATH. `from_login_shell()` probes the
/// user's login shell to capture the full PATH, so adapters can find binaries
/// like `claude`, `nvim`, `yazi`, etc.
#[derive(Debug, Clone)]
pub struct SystemContext {
    pub path: String,
    pub shell: String,
}

impl SystemContext {
    /// Probe the login shell for the full PATH. Cached by caller.
    pub fn from_login_shell() -> Self {
        let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/zsh".into());
        let path = std::process::Command::new(&shell)
            .args(["-l", "-c", "source ~/.zshrc 2>/dev/null; printf '%s' \"$PATH\""])
            .stdin(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .output()
            .ok()
            .filter(|o| o.status.success())
            .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| std::env::var("PATH").unwrap_or_default());
        Self { path, shell }
    }

    /// Resolve a binary name to its absolute path using this context's PATH.
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
    fn manifest(&self) -> &AdapterManifest;

    /// Check whether the adapter's backing binary is available.
    fn is_available(&self) -> bool;
}

// ---------------------------------------------------------------------------
// Chat capability
// ---------------------------------------------------------------------------

/// Events emitted by a chat backend during a conversation turn.
#[derive(Debug, Clone)]
pub enum ChatEvent {
    Start { backend: String },
    Text { chunk: String },
    Done { exit_code: i32, full_text: String },
    Error { message: String },
}

/// Headless agent backend (claude, opencode, etc.)
///
/// Threading contract: `send_message` spawns a background thread that
/// pushes events to the provided `Sender`. The caller owns the `Receiver`
/// and drains it. The adapter must send `Done` or `Error` as the final
/// event and then drop the sender.
pub trait ChatCapability: Capability {
    /// Spawn the agent CLI. Push streaming events to `tx`.
    /// Returns immediately — work happens on a background thread.
    fn send_message(
        &self,
        message: &str,
        cwd: &str,
        tx: mpsc::Sender<ChatEvent>,
    ) -> Result<(), NexusError>;

    /// For mux-hosted surfaces (tmux): return the shell command to launch
    /// the agent interactively in a pane. None if not supported.
    fn get_launch_command(&self) -> Option<String>;
}

// ---------------------------------------------------------------------------
// Editor capability
// ---------------------------------------------------------------------------

/// Text editor backend (neovim, helix, etc.)
pub trait EditorCapability: Capability {
    fn open(&mut self, path: &str, line: u32, col: u32) -> Result<(), NexusError>;
    fn get_current_buffer(&self) -> Option<String>;
    fn get_buffer_content(&self, max_lines: u32) -> Option<String>;
    fn apply_edit(&mut self, patch: &str) -> Result<(), NexusError>;
    fn get_tabs(&self) -> Vec<HashMap<String, String>>;
    fn send_command(&mut self, cmd: &str) -> Result<(), NexusError>;
    fn remote_expr(&self, expr: &str) -> Option<String>;
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

/// File explorer backend (yazi, ranger, built-in fs)
pub trait ExplorerCapability: Capability {
    fn list_directory(&self, path: &str) -> Result<Vec<DirEntry>, NexusError>;
    fn get_selection(&self) -> Option<String>;
    fn trigger_action(&mut self, action: &str, payload: &str) -> Result<(), NexusError>;
    fn get_launch_command(&self) -> Option<String>;
}

// ---------------------------------------------------------------------------
// Browser capability
// ---------------------------------------------------------------------------

/// Web browser backend (xterm.js w3m fallback, Tauri WebView, Ladybird)
pub trait BrowserCapability: Capability {
    fn load_url(&mut self, url: &str) -> Result<(), NexusError>;
    fn get_current_url(&self) -> Option<String>;
    fn query_selector(&self, selector: &str) -> Result<String, NexusError>;
    fn is_alive(&self) -> bool;
    fn get_launch_command(&self) -> Option<String>;
}

// ---------------------------------------------------------------------------
// RichText capability (Obsidian Parity)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoteNode {
    pub id: String,
    pub path: String,
    pub title: String,
    pub content: String,
    pub tags: Vec<String>,
    pub backlinks: Vec<String>,
}

pub trait RichTextCapability: Capability {
    /// Open a "Vault" (directory)
    fn open_vault(&mut self, path: &str) -> Result<(), NexusError>;
    /// Load a node by its ID or path
    fn load_node(&mut self, id_or_path: &str) -> Result<NoteNode, NexusError>;
    /// Save node content
    fn save_node(&mut self, node: NoteNode) -> Result<(), NexusError>;
    /// Search for nodes by tag or title
    fn search_nodes(&self, query: &str) -> Result<Vec<NoteNode>, NexusError>;
    /// Get all nodes in the current vault
    fn list_nodes(&self) -> Result<Vec<NoteNode>, NexusError>;
}

// ---------------------------------------------------------------------------
// HUD Capability
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HUDPart {
    pub id: String,
    pub part_type: String, // "Gauge", "Sparkline", "Matrix", "Graph", "Timeline"
    pub label: String,
    pub value: serde_json::Value,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HUDFrame {
    pub source: String,
    pub parts: Vec<HUDPart>,
    pub timestamp: String,
}

pub trait HUDCapability: Capability + Send + Sync {
    /// Get a single snapshot of HUD data
    fn get_frame(&self) -> Result<HUDFrame, NexusError>;
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
