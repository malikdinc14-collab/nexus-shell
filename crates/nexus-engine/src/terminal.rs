//! Terminal module — ABC trait + adapter registry.
//!
//! Non-native module: external shells (bash, zsh, fish) are the real
//! engines. We define the trait they must satisfy and a thin orchestrator
//! that manages terminal sessions per pane.
//!
//! The existing PtyManager handles low-level PTY I/O. This module adds
//! the abstraction layer for shell selection and session metadata.

use nexus_core::NexusError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::content_tabs::{ContentTab, ContentTabState, TabProvider};

// ---------------------------------------------------------------------------
// ABC — the contract any terminal backend must satisfy
// ---------------------------------------------------------------------------

/// Metadata about a terminal backend (shell).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShellInfo {
    pub name: String,
    pub path: String,
    pub version: Option<String>,
}

/// A running terminal session.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TerminalSession {
    pub pane_id: String,
    pub shell: String,
    pub cwd: Option<String>,
    pub title: Option<String>,
    pub pid: Option<u32>,
}

/// Any terminal backend implements this trait.
pub trait TerminalBackend: Send {
    /// The shell binary path (e.g. "/bin/zsh").
    fn shell_path(&self) -> &str;

    /// Human-readable name.
    fn name(&self) -> &str;

    /// Whether this shell is available on the system.
    fn is_available(&self) -> bool;

    /// Shell info.
    fn info(&self) -> ShellInfo;
}

// ---------------------------------------------------------------------------
// Built-in adapter: SystemShell — uses the user's login shell
// ---------------------------------------------------------------------------

pub struct SystemShell {
    path: String,
    name: String,
}

impl SystemShell {
    pub fn new() -> Self {
        let path = std::env::var("SHELL").unwrap_or_else(|_| "/bin/sh".into());
        let name = path.rsplit('/').next().unwrap_or("sh").to_string();
        Self { path, name }
    }

    pub fn from_path(path: &str) -> Self {
        let name = path.rsplit('/').next().unwrap_or("sh").to_string();
        Self {
            path: path.to_string(),
            name,
        }
    }
}

impl TerminalBackend for SystemShell {
    fn shell_path(&self) -> &str {
        &self.path
    }

    fn name(&self) -> &str {
        &self.name
    }

    fn is_available(&self) -> bool {
        std::path::Path::new(&self.path).exists()
    }

    fn info(&self) -> ShellInfo {
        ShellInfo {
            name: self.name.clone(),
            path: self.path.clone(),
            version: None,
        }
    }
}

// ---------------------------------------------------------------------------
// Orchestrator — manages terminal sessions, delegates to backend
// ---------------------------------------------------------------------------

/// Multiple sessions per pane with an active index.
#[derive(Debug, Clone)]
struct PaneSessions {
    items: Vec<TerminalSession>,
    active: usize,
}

impl PaneSessions {
    fn new() -> Self {
        Self { items: Vec::new(), active: 0 }
    }
}

pub struct Terminal {
    backend: Box<dyn TerminalBackend>,
    sessions: HashMap<String, PaneSessions>, // keyed by pane_id
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TerminalState {
    pub backend: String,
    pub shell_path: String,
    pub sessions: Vec<TerminalSession>,
}

impl Terminal {
    pub fn new() -> Self {
        Self {
            backend: Box::new(SystemShell::new()),
            sessions: HashMap::new(),
        }
    }

    pub fn with_backend(backend: Box<dyn TerminalBackend>) -> Self {
        Self {
            backend,
            sessions: HashMap::new(),
        }
    }

    pub fn set_backend(&mut self, backend: Box<dyn TerminalBackend>) {
        self.backend = backend;
    }

    pub fn backend_name(&self) -> &str {
        self.backend.name()
    }

    pub fn shell_path(&self) -> &str {
        self.backend.shell_path()
    }

    pub fn info(&self) -> ShellInfo {
        self.backend.info()
    }

    /// Register a new terminal session for a pane.
    /// Idempotent: if the pane already has sessions, returns the active one.
    pub fn register_session(&mut self, pane_id: &str, cwd: Option<&str>) -> &TerminalSession {
        let pane = self.sessions.entry(pane_id.to_string()).or_insert_with(PaneSessions::new);
        // Don't push duplicate sessions on re-mount
        if !pane.items.is_empty() {
            return &pane.items[pane.active];
        }
        let session = TerminalSession {
            pane_id: pane_id.to_string(),
            shell: self.backend.name().to_string(),
            cwd: cwd.map(String::from),
            title: None,
            pid: None,
        };
        pane.items.push(session);
        pane.active = pane.items.len() - 1;
        &pane.items[pane.active]
    }

    /// Remove all sessions for a pane (called on unmount).
    pub fn remove_sessions(&mut self, pane_id: &str) {
        self.sessions.remove(pane_id);
    }

    /// Update active session metadata (title, pid, cwd).
    pub fn update_session(&mut self, pane_id: &str, title: Option<&str>, pid: Option<u32>, cwd: Option<&str>) {
        if let Some(pane) = self.sessions.get_mut(pane_id) {
            if let Some(session) = pane.items.get_mut(pane.active) {
                if let Some(t) = title { session.title = Some(t.to_string()); }
                if let Some(p) = pid { session.pid = Some(p); }
                if let Some(c) = cwd { session.cwd = Some(c.to_string()); }
            }
        }
    }

    /// Remove active session. Returns true if removed.
    pub fn remove_session(&mut self, pane_id: &str) -> bool {
        let pane = match self.sessions.get_mut(pane_id) {
            Some(p) => p,
            None => return false,
        };
        if pane.items.is_empty() {
            self.sessions.remove(pane_id);
            return false;
        }
        pane.items.remove(pane.active);
        if pane.items.is_empty() {
            self.sessions.remove(pane_id);
        } else if pane.active >= pane.items.len() {
            pane.active = pane.items.len() - 1;
        }
        true
    }

    /// Get active session by pane_id.
    pub fn session(&self, pane_id: &str) -> Option<&TerminalSession> {
        let pane = self.sessions.get(pane_id)?;
        pane.items.get(pane.active)
    }

    /// List all sessions across all panes.
    pub fn sessions(&self) -> Vec<&TerminalSession> {
        self.sessions.values().flat_map(|p| p.items.iter()).collect()
    }

    /// Full state for surfaces.
    pub fn state(&self) -> TerminalState {
        TerminalState {
            backend: self.backend.name().to_string(),
            shell_path: self.backend.shell_path().to_string(),
            sessions: self.sessions.values().flat_map(|p| p.items.clone()).collect(),
        }
    }
}

// ---------------------------------------------------------------------------
// TabProvider implementation
// ---------------------------------------------------------------------------

impl TabProvider for Terminal {
    fn content_tabs(&self, pane_id: &str) -> Option<ContentTabState> {
        let pane = self.sessions.get(pane_id)?;
        if pane.items.is_empty() {
            return None;
        }
        Some(ContentTabState {
            tabs: pane.items.iter().enumerate().map(|(i, s)| ContentTab {
                id: format!("{}-{}", s.pane_id, i),
                name: s.title.clone().unwrap_or_else(|| s.shell.clone()),
                modified: false,
                preview: false,
            }).collect(),
            active: pane.active,
        })
    }

    fn switch_content_tab(&mut self, pane_id: &str, index: usize) -> Result<ContentTabState, NexusError> {
        let pane = self.sessions.get_mut(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no sessions in {pane_id}")))?;
        if index >= pane.items.len() {
            return Err(NexusError::InvalidState(format!("index {index} out of range ({})", pane.items.len())));
        }
        pane.active = index;
        self.content_tabs(pane_id).ok_or_else(|| NexusError::Other("unreachable".into()))
    }

    fn close_content_tab(&mut self, pane_id: &str, index: usize) -> Result<Option<ContentTabState>, NexusError> {
        let pane = self.sessions.get_mut(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no sessions in {pane_id}")))?;
        if index >= pane.items.len() {
            return Err(NexusError::InvalidState(format!("index {index} out of range ({})", pane.items.len())));
        }
        pane.items.remove(index);
        if pane.items.is_empty() {
            self.sessions.remove(pane_id);
            return Ok(None);
        }
        if pane.active >= pane.items.len() {
            pane.active = pane.items.len() - 1;
        }
        Ok(self.content_tabs(pane_id))
    }

    fn supports_content_tabs(&self) -> bool { true }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn system_shell_detects() {
        let shell = SystemShell::new();
        assert!(!shell.name().is_empty());
        assert!(!shell.shell_path().is_empty());
    }

    #[test]
    fn from_path() {
        let shell = SystemShell::from_path("/bin/zsh");
        assert_eq!(shell.name(), "zsh");
        assert_eq!(shell.shell_path(), "/bin/zsh");
    }

    #[test]
    fn session_lifecycle() {
        let mut term = Terminal::new();

        // Register
        let session = term.register_session("pane-1", Some("/home"));
        assert_eq!(session.pane_id, "pane-1");
        assert_eq!(session.cwd, Some("/home".into()));

        // Update
        term.update_session("pane-1", Some("vim"), Some(1234), None);
        let s = term.session("pane-1").unwrap();
        assert_eq!(s.title, Some("vim".into()));
        assert_eq!(s.pid, Some(1234));

        // List
        assert_eq!(term.sessions().len(), 1);

        // Remove
        assert!(term.remove_session("pane-1"));
        assert!(term.session("pane-1").is_none());
    }

    #[test]
    fn backend_swappable() {
        struct FishBackend;
        impl TerminalBackend for FishBackend {
            fn shell_path(&self) -> &str { "/usr/bin/fish" }
            fn name(&self) -> &str { "fish" }
            fn is_available(&self) -> bool { false }
            fn info(&self) -> ShellInfo {
                ShellInfo { name: "fish".into(), path: "/usr/bin/fish".into(), version: Some("3.7".into()) }
            }
        }

        let mut term = Terminal::new();
        term.set_backend(Box::new(FishBackend));
        assert_eq!(term.backend_name(), "fish");
        assert_eq!(term.shell_path(), "/usr/bin/fish");
    }

    #[test]
    fn state_snapshot() {
        let mut term = Terminal::new();
        term.register_session("p1", Some("/tmp"));
        term.register_session("p2", None);
        let state = term.state();
        assert_eq!(state.sessions.len(), 2);
        assert!(!state.backend.is_empty());
    }
}
