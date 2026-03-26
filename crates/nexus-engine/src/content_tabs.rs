//! Content Tabs — sub-tab system within modules.
//!
//! Modules that support multiple items per pane (editor buffers, terminal
//! sessions, chat conversations) implement `TabProvider` to expose their
//! internal items as content tabs. The engine owns this state; surfaces
//! render it via the `content.*` dispatch domain.
//!
//! This sits alongside StackManager (which handles module-level tabs like
//! Editor/Terminal/Chat). StackManager = which module; TabProvider = which
//! item within that module.

use serde::{Deserialize, Serialize};

/// Metadata for a single content tab within a module.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentTab {
    /// Unique key (file path, session id, conversation id).
    pub id: String,
    /// Display name ("main.rs", "zsh", "claude").
    pub name: String,
    /// Unsaved changes indicator.
    pub modified: bool,
    /// Preview tab — auto-replaced on next open (like VS Code preview tabs).
    pub preview: bool,
}

/// Snapshot of all content tabs for a pane within a module.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentTabState {
    pub tabs: Vec<ContentTab>,
    /// Index of the active tab in `tabs`.
    pub active: usize,
}

/// Trait for modules that support multiple content items per pane.
///
/// Modules like Editor (multiple buffers), Terminal (multiple sessions),
/// and Chat (multiple conversations) implement this. Explorer and other
/// single-view modules don't need to.
pub trait TabProvider: Send {
    /// List content tabs for a pane. Returns None if this module has
    /// no items open in this pane.
    fn content_tabs(&self, pane_id: &str) -> Option<ContentTabState>;

    /// Switch to content tab by index within a pane.
    fn switch_content_tab(
        &mut self,
        pane_id: &str,
        index: usize,
    ) -> Result<ContentTabState, String>;

    /// Close content tab by index. Returns updated state, or None if
    /// no tabs remain after closing.
    fn close_content_tab(
        &mut self,
        pane_id: &str,
        index: usize,
    ) -> Result<Option<ContentTabState>, String>;

    /// Whether this module supports multiple content tabs per pane.
    fn supports_content_tabs(&self) -> bool {
        false
    }
}

// ── Tests ───────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn content_tab_serializes() {
        let tab = ContentTab {
            id: "/tmp/main.rs".into(),
            name: "main.rs".into(),
            modified: true,
            preview: false,
        };
        let json = serde_json::to_value(&tab).unwrap();
        assert_eq!(json["name"], "main.rs");
        assert_eq!(json["modified"], true);
    }

    #[test]
    fn content_tab_state_serializes() {
        let state = ContentTabState {
            tabs: vec![
                ContentTab {
                    id: "a.rs".into(),
                    name: "a.rs".into(),
                    modified: false,
                    preview: false,
                },
                ContentTab {
                    id: "b.rs".into(),
                    name: "b.rs".into(),
                    modified: true,
                    preview: false,
                },
            ],
            active: 1,
        };
        let json = serde_json::to_value(&state).unwrap();
        assert_eq!(json["active"], 1);
        assert_eq!(json["tabs"].as_array().unwrap().len(), 2);
    }
}
