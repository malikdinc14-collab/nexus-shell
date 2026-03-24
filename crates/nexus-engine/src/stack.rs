//! Tab and TabStack data models for nexus-shell tab management.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

use crate::surface::Geometry;

// ---------------------------------------------------------------------------
// Tab
// ---------------------------------------------------------------------------

/// A single logical tab within a TabStack.
///
/// Represents one running tool (editor, terminal, chat, menu, etc.)
/// that can be attached to a surface container or shelved in the reservoir.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tab {
    pub id: String,
    pub pane_handle: Option<String>,
    pub name: String,
    pub command: String,
    pub cwd: String,
    pub role: Option<String>,
    pub env: HashMap<String, String>,
    pub is_active: bool,
    pub status: TabStatus,
    pub geometry: Option<Geometry>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TabStatus {
    Visible,
    Background,
}

impl Tab {
    pub fn new(name: &str) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            pane_handle: None,
            name: name.to_string(),
            command: String::new(),
            cwd: String::new(),
            role: None,
            env: HashMap::new(),
            is_active: false,
            status: TabStatus::Background,
            geometry: None,
        }
    }

    pub fn with_handle(mut self, handle: &str) -> Self {
        self.pane_handle = Some(handle.to_string());
        self
    }

    pub fn with_status(mut self, status: TabStatus, active: bool) -> Self {
        self.status = status;
        self.is_active = active;
        self
    }
}

// ---------------------------------------------------------------------------
// TabStack
// ---------------------------------------------------------------------------

/// An ordered collection of Tabs assigned to one surface container.
///
/// Only one Tab is active (visible) at a time. Push, pop, and rotate
/// operations switch between tabs atomically.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TabStack {
    pub id: String,
    pub pane_id: String,
    pub tabs: Vec<Tab>,
    pub active_index: usize,
    pub role: Option<String>,
    pub tags: Vec<String>,
    pub metadata: HashMap<String, String>,
}

impl TabStack {
    pub fn new(pane_id: &str) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            pane_id: pane_id.to_string(),
            tabs: Vec::new(),
            active_index: 0,
            role: None,
            tags: Vec::new(),
            metadata: HashMap::new(),
        }
    }

    pub fn with_id(mut self, id: &str) -> Self {
        self.id = id.to_string();
        self
    }

    /// Return the currently active Tab, or None if empty.
    pub fn active_tab(&self) -> Option<&Tab> {
        if self.tabs.is_empty() {
            return None;
        }
        let idx = self.active_index.min(self.tabs.len() - 1);
        Some(&self.tabs[idx])
    }

    /// Push a tab onto the stack and make it active.
    pub fn push(&mut self, mut tab: Tab) {
        if let Some(current) = self.tabs.get_mut(self.active_index) {
            current.is_active = false;
            current.status = TabStatus::Background;
        }
        tab.pane_handle = Some(self.pane_id.clone());
        tab.is_active = true;
        tab.status = TabStatus::Visible;
        self.tabs.push(tab);
        self.active_index = self.tabs.len() - 1;
    }

    /// Remove and return the active tab. Activates the next tab.
    pub fn pop(&mut self) -> Option<Tab> {
        if self.tabs.is_empty() {
            return None;
        }
        let mut tab = self.tabs.remove(self.active_index);
        tab.is_active = false;
        tab.status = TabStatus::Background;
        tab.pane_handle = None;

        if !self.tabs.is_empty() {
            self.active_index = self.active_index.min(self.tabs.len() - 1);
            self.tabs[self.active_index].is_active = true;
            self.tabs[self.active_index].status = TabStatus::Visible;
        } else {
            self.active_index = 0;
        }
        Some(tab)
    }

    /// Rotate the active tab by direction (+1 forward, -1 backward).
    pub fn rotate(&mut self, direction: i32) {
        let len = self.tabs.len();
        if len <= 1 {
            return;
        }
        self.tabs[self.active_index].is_active = false;
        self.tabs[self.active_index].status = TabStatus::Background;

        let new_idx = ((self.active_index as i64 + direction as i64).rem_euclid(len as i64)) as usize;
        self.active_index = new_idx;

        self.tabs[self.active_index].is_active = true;
        self.tabs[self.active_index].status = TabStatus::Visible;
    }

    /// Serialize to JSON-compatible format.
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "role": self.role,
            "tags": self.tags,
            "active_index": self.active_index,
            "tabs": self.tabs.iter().map(|t| {
                serde_json::json!({
                    "id": t.pane_handle.as_deref().unwrap_or(&t.id),
                    "name": t.name,
                    "status": format!("{:?}", t.status).to_uppercase(),
                    "geometry": t.geometry,
                })
            }).collect::<Vec<_>>(),
            "metadata": self.metadata,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn push_makes_tab_active() {
        let mut stack = TabStack::new("pane1");
        stack.push(Tab::new("Shell"));
        assert_eq!(stack.tabs.len(), 1);
        assert!(stack.tabs[0].is_active);
        assert_eq!(stack.tabs[0].status, TabStatus::Visible);
    }

    #[test]
    fn push_deactivates_previous() {
        let mut stack = TabStack::new("pane1");
        stack.push(Tab::new("First"));
        stack.push(Tab::new("Second"));
        assert!(!stack.tabs[0].is_active);
        assert_eq!(stack.tabs[0].status, TabStatus::Background);
        assert!(stack.tabs[1].is_active);
        assert_eq!(stack.active_index, 1);
    }

    #[test]
    fn pop_returns_active_and_activates_next() {
        let mut stack = TabStack::new("pane1");
        stack.push(Tab::new("First"));
        stack.push(Tab::new("Second"));

        let popped = stack.pop().unwrap();
        assert_eq!(popped.name, "Second");
        assert!(!popped.is_active);
        assert_eq!(stack.tabs.len(), 1);
        assert!(stack.tabs[0].is_active);
    }

    #[test]
    fn pop_empty_returns_none() {
        let mut stack = TabStack::new("pane1");
        assert!(stack.pop().is_none());
    }

    #[test]
    fn rotate_forward() {
        let mut stack = TabStack::new("pane1");
        stack.push(Tab::new("A"));
        stack.push(Tab::new("B"));
        stack.push(Tab::new("C"));
        assert_eq!(stack.active_index, 2);

        stack.rotate(1); // wraps to 0
        assert_eq!(stack.active_index, 0);
        assert!(stack.tabs[0].is_active);
        assert!(!stack.tabs[2].is_active);
    }

    #[test]
    fn rotate_backward() {
        let mut stack = TabStack::new("pane1");
        stack.push(Tab::new("A"));
        stack.push(Tab::new("B"));
        stack.push(Tab::new("C"));

        stack.rotate(-1); // 2 -> 1
        assert_eq!(stack.active_index, 1);
    }

    #[test]
    fn rotate_single_tab_noop() {
        let mut stack = TabStack::new("pane1");
        stack.push(Tab::new("Only"));
        stack.rotate(1);
        assert_eq!(stack.active_index, 0);
    }

    #[test]
    fn active_tab_returns_correct() {
        let mut stack = TabStack::new("pane1");
        assert!(stack.active_tab().is_none());
        stack.push(Tab::new("First"));
        assert_eq!(stack.active_tab().unwrap().name, "First");
    }
}
