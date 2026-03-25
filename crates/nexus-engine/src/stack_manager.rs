//! StackManager — runtime manager that tracks all TabStacks across all panes.

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::stack::{Tab, TabStack, TabStatus};

// ---------------------------------------------------------------------------
// Sentinel types
// ---------------------------------------------------------------------------

/// Returned when pop() would remove the last tab.
#[derive(Debug)]
pub struct LastTabWarning;

/// Returned when an operation is delegated to a native tab system.
#[derive(Debug)]
pub struct NativelyManaged;

/// Result of a stack operation that may return a sentinel.
#[derive(Debug)]
#[allow(clippy::large_enum_variant)]
pub enum StackOpResult {
    Ok(Option<Tab>),
    LastTab(LastTabWarning),
    Native(NativelyManaged),
    NotFound,
}

// ---------------------------------------------------------------------------
// StackManager
// ---------------------------------------------------------------------------

/// Maps stack IDs to TabStack instances and manages tab operations.
///
/// Supports identity-based lookup (role, tag, UUID) matching the daemon's
/// resolution semantics.
#[derive(Debug, Clone, Serialize)]
pub struct StackManager {
    stacks: HashMap<String, TabStack>,
    id_counter: u32,
}

impl<'de> Deserialize<'de> for StackManager {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        #[derive(Deserialize)]
        struct Raw {
            stacks: HashMap<String, TabStack>,
            id_counter: u32,
        }

        let raw = Raw::deserialize(deserializer)?;

        let max_id = raw
            .stacks
            .keys()
            .filter_map(|k| k.strip_prefix("stack_"))
            .filter_map(|hex| u32::from_str_radix(hex, 16).ok())
            .max()
            .unwrap_or(0);

        let id_counter = raw.id_counter.max(max_id);

        Ok(StackManager {
            stacks: raw.stacks,
            id_counter,
        })
    }
}

impl StackManager {
    pub fn new() -> Self {
        Self {
            stacks: HashMap::new(),
            id_counter: 0,
        }
    }

    fn next_stack_id(&mut self) -> String {
        self.id_counter += 1;
        format!("stack_{:06x}", self.id_counter)
    }

    // -- Identity resolution -------------------------------------------------

    /// Resolve a stack by UUID, role, or tag.
    pub fn get_by_identity<'a>(&'a self, identity: &'a str) -> Option<(&'a str, &'a TabStack)> {
        // Direct ID match
        if let Some(stack) = self.stacks.get(identity) {
            return Some((identity, stack));
        }
        // Role match
        for (sid, stack) in &self.stacks {
            if stack.role.as_deref() == Some(identity) {
                return Some((sid, stack));
            }
        }
        // Tag match
        for (sid, stack) in &self.stacks {
            if stack.tags.contains(&identity.to_string()) {
                return Some((sid, stack));
            }
        }
        None
    }

    /// Mutable version of get_by_identity.
    pub fn get_by_identity_mut(&mut self, identity: &str) -> Option<(String, &mut TabStack)> {
        // Direct ID match
        if self.stacks.contains_key(identity) {
            let stack = self.stacks.get_mut(identity).unwrap();
            return Some((identity.to_string(), stack));
        }
        // Role match
        let role_match = self
            .stacks
            .iter()
            .find(|(_, s)| s.role.as_deref() == Some(identity))
            .map(|(k, _)| k.clone());
        if let Some(sid) = role_match {
            return Some((sid.clone(), self.stacks.get_mut(&sid).unwrap()));
        }
        // Tag match
        let tag_match = self
            .stacks
            .iter()
            .find(|(_, s)| s.tags.contains(&identity.to_string()))
            .map(|(k, _)| k.clone());
        if let Some(sid) = tag_match {
            return Some((sid.clone(), self.stacks.get_mut(&sid).unwrap()));
        }
        None
    }

    /// Resolve or create a stack by identity.
    pub fn get_or_create_by_identity(
        &mut self,
        identity: &str,
        initial_pane: Option<&str>,
    ) -> (String, &mut TabStack) {
        // Try existing lookup first
        let existing_sid = {
            if self.stacks.contains_key(identity) {
                Some(identity.to_string())
            } else {
                self.stacks
                    .iter()
                    .find(|(_, s)| {
                        s.role.as_deref() == Some(identity)
                            || s.tags.contains(&identity.to_string())
                    })
                    .map(|(k, _)| k.clone())
            }
        };

        if let Some(sid) = existing_sid {
            let stack = self.stacks.get_mut(&sid).unwrap();
            return (sid, stack);
        }

        // Create new
        let is_uuid = identity.starts_with("stack_");
        let sid = if is_uuid {
            identity.to_string()
        } else {
            self.next_stack_id()
        };
        let role = if is_uuid {
            None
        } else {
            Some(identity.to_string())
        };

        let mut stack = TabStack::new(&sid).with_id(&sid);
        stack.role = role;

        if let Some(pane) = initial_pane {
            let role_name = if !is_uuid {
                let mut c = identity.chars();
                match c.next() {
                    None => "Shell".to_string(),
                    Some(first) => {
                        first.to_uppercase().to_string() + c.as_str()
                    }
                }
            } else {
                "Shell".to_string()
            };
            let tab = Tab::new(&role_name)
                .with_handle(pane)
                .with_status(TabStatus::Visible, true);
            stack.tabs.push(tab);
        }

        self.stacks.insert(sid.clone(), stack);
        let stack = self.stacks.get_mut(&sid).unwrap();
        (sid, stack)
    }

    /// Return the existing stack for an ID, or None.
    pub fn get_stack(&self, id: &str) -> Option<&TabStack> {
        self.stacks.get(id)
    }

    pub fn get_stack_mut(&mut self, id: &str) -> Option<&mut TabStack> {
        self.stacks.get_mut(id)
    }

    // -- Operations ----------------------------------------------------------

    /// Push a tab onto a stack.
    pub fn push(&mut self, stack_id: &str, tab: Tab) -> StackOpResult {
        if let Some(stack) = self.stacks.get_mut(stack_id) {
            stack.push(tab);
            StackOpResult::Ok(None)
        } else {
            StackOpResult::NotFound
        }
    }

    /// Pop the active tab from a stack.
    pub fn pop(&mut self, stack_id: &str) -> StackOpResult {
        if let Some(stack) = self.stacks.get_mut(stack_id) {
            if stack.tabs.is_empty() {
                return StackOpResult::Ok(None);
            }
            if stack.tabs.len() == 1 {
                return StackOpResult::LastTab(LastTabWarning);
            }
            StackOpResult::Ok(stack.pop())
        } else {
            StackOpResult::NotFound
        }
    }

    /// Rotate tabs in a stack.
    pub fn rotate(&mut self, stack_id: &str, direction: i32) -> StackOpResult {
        if let Some(stack) = self.stacks.get_mut(stack_id) {
            stack.rotate(direction);
            StackOpResult::Ok(stack.active_tab().cloned())
        } else {
            StackOpResult::NotFound
        }
    }

    /// Remove a stack entirely.
    pub fn remove_stack(&mut self, stack_id: &str) {
        self.stacks.remove(stack_id);
    }

    /// All tracked stacks.
    pub fn all_stacks(&self) -> &HashMap<String, TabStack> {
        &self.stacks
    }

    // -- Scrubbing -----------------------------------------------------------

    /// Remove stacks with dead containers. Returns removed stack IDs.
    pub fn scrub(&mut self, container_exists: impl Fn(&str) -> bool) -> Vec<String> {
        let mut dead = Vec::new();

        for (sid, stack) in self.stacks.iter_mut() {
            let live_tabs: Vec<Tab> = stack
                .tabs
                .iter()
                .filter(|t| {
                    t.pane_handle
                        .as_ref()
                        .map(|h| container_exists(h))
                        .unwrap_or(false)
                })
                .cloned()
                .collect();

            if live_tabs.is_empty() {
                dead.push(sid.clone());
            } else if live_tabs.len() != stack.tabs.len() {
                stack.tabs = live_tabs;
                stack.active_index = stack.active_index.min(stack.tabs.len() - 1);
            }
        }

        for sid in &dead {
            self.stacks.remove(sid);
        }
        dead
    }

    // -- Serialization -------------------------------------------------------

    pub fn serialize(&self) -> serde_json::Value {
        let stacks: serde_json::Map<String, serde_json::Value> = self
            .stacks
            .iter()
            .map(|(sid, stack)| (sid.clone(), stack.to_json()))
            .collect();
        serde_json::json!({ "stacks": stacks })
    }
}

impl Default for StackManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn get_or_create_by_role() {
        let mut mgr = StackManager::new();
        let (sid1, _) = mgr.get_or_create_by_identity("editor", Some("pane1"));
        let (sid2, _) = mgr.get_or_create_by_identity("editor", Some("pane2"));
        assert_eq!(sid1, sid2, "same role should return same stack");
    }

    #[test]
    fn get_or_create_new_stack_id() {
        let mut mgr = StackManager::new();
        let (sid, _) = mgr.get_or_create_by_identity("terminal", None);
        assert!(sid.starts_with("stack_"));
    }

    #[test]
    fn get_by_identity_role_lookup() {
        let mut mgr = StackManager::new();
        mgr.get_or_create_by_identity("editor", Some("pane1"));

        let result = mgr.get_by_identity("editor");
        assert!(result.is_some());
        assert_eq!(result.unwrap().1.role.as_deref(), Some("editor"));
    }

    #[test]
    fn get_by_identity_tag_lookup() {
        let mut mgr = StackManager::new();
        let (sid, stack) = mgr.get_or_create_by_identity("mystack", None);
        stack.tags.push("important".to_string());

        let result = mgr.get_by_identity("important");
        assert!(result.is_some());
        assert_eq!(result.unwrap().0, sid);
    }

    #[test]
    fn scrub_removes_dead_stacks() {
        let mut mgr = StackManager::new();
        let (sid, _) = mgr.get_or_create_by_identity("dead_stack", Some("dead_pane"));

        let removed = mgr.scrub(|_handle| false);
        assert_eq!(removed, vec![sid]);
        assert!(mgr.all_stacks().is_empty());
    }

    #[test]
    fn scrub_keeps_live_stacks() {
        let mut mgr = StackManager::new();
        mgr.get_or_create_by_identity("live", Some("pane1"));

        let removed = mgr.scrub(|_| true);
        assert!(removed.is_empty());
        assert_eq!(mgr.all_stacks().len(), 1);
    }

    #[test]
    fn pop_last_tab_returns_warning() {
        let mut mgr = StackManager::new();
        let (sid, _) = mgr.get_or_create_by_identity("single", Some("pane1"));
        match mgr.pop(&sid) {
            StackOpResult::LastTab(_) => {}
            other => panic!("expected LastTab, got {:?}", other),
        }
    }

    #[test]
    fn stackmanager_roundtrip_serde() {
        let mut mgr = StackManager::new();
        mgr.get_or_create_by_identity("editor", Some("pane1"));
        mgr.get_or_create_by_identity("terminal", Some("pane2"));

        let json = serde_json::to_string(&mgr).unwrap();
        let restored: StackManager = serde_json::from_str(&json).unwrap();

        assert_eq!(restored.all_stacks().len(), 2);
        assert!(restored.get_by_identity("editor").is_some());
        assert!(restored.get_by_identity("terminal").is_some());
    }

    #[test]
    fn stackmanager_id_counter_preserved() {
        let mut mgr = StackManager::new();
        mgr.get_or_create_by_identity("a", None);
        mgr.get_or_create_by_identity("b", None);

        let json = serde_json::to_string(&mgr).unwrap();
        let mut restored: StackManager = serde_json::from_str(&json).unwrap();

        let (sid, _) = restored.get_or_create_by_identity("c", None);
        assert_eq!(sid, "stack_000003");
    }

    #[test]
    fn stackmanager_id_counter_recomputed_if_too_low() {
        let json = r#"{"stacks":{"stack_000005":{"id":"stack_000005","pane_id":"stack_000005","tabs":[],"active_index":0,"role":null,"tags":[],"metadata":{}}},"id_counter":1}"#;
        let mut restored: StackManager = serde_json::from_str(json).unwrap();

        let (sid, _) = restored.get_or_create_by_identity("new", None);
        assert_eq!(sid, "stack_000006");
    }
}
