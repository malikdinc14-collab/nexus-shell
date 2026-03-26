//! NexusCore — the single entry point for all Nexus Shell operations.
//!
//! The core is mux-agnostic. Inject a Mux implementation at
//! construction time. All state lives here; the mux is a dumb backend.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use crate::bus::{EventBus, EventType, TypedEvent};
use crate::layout::LayoutTree;
use crate::persistence::{PaneState, WorkspaceSave};
use crate::pty::PtyManager;
use crate::registry::CapabilityRegistry;
use crate::stack::{Tab, TabStack, TabStatus};
use crate::stack_manager::StackManager;
use crate::surface::{Mux, SurfaceRegistry};
use nexus_core::capability::SystemContext;

/// Find the visible container in a stack given the focused pane.
fn get_visible_container(stack: &TabStack, focused_id: &str) -> Option<String> {
    if stack.tabs.is_empty() {
        return None;
    }
    for tab in &stack.tabs {
        if tab.pane_handle.as_deref() == Some(focused_id) {
            return Some(focused_id.to_string());
        }
    }
    for tab in &stack.tabs {
        if tab.status == TabStatus::Visible {
            return tab.pane_handle.clone();
        }
    }
    stack.active_tab().and_then(|t| t.pane_handle.clone())
}

/// Result of a stack operation, returned as JSON-compatible data.
#[derive(Debug, Clone)]
pub struct OpResult {
    pub status: String,
    pub data: HashMap<String, serde_json::Value>,
}

impl OpResult {
    pub fn ok() -> Self {
        Self {
            status: "ok".into(),
            data: HashMap::new(),
        }
    }

    pub fn ok_with(key: &str, value: impl Into<serde_json::Value>) -> Self {
        let mut data = HashMap::new();
        data.insert(key.to_string(), value.into());
        Self {
            status: "ok".into(),
            data,
        }
    }

    pub fn error(err: &str) -> Self {
        let mut data = HashMap::new();
        data.insert("error".to_string(), serde_json::Value::String(err.into()));
        Self {
            status: "error".into(),
            data,
        }
    }
}

/// Facade wrapping all engine modules behind a mux-agnostic API.
pub struct NexusCore {
    pub mux: Box<dyn Mux>,
    pub registry: Option<CapabilityRegistry>,
    pub stacks: StackManager,
    pub bus: Arc<Mutex<EventBus>>,
    pub layout: LayoutTree,
    pub surfaces: SurfaceRegistry,
    pty: PtyManager,
    session: Option<String>,
    dirty: bool,
    cwd: String,
}

impl NexusCore {
    pub fn new(mux: Box<dyn Mux>) -> Self {
        Self {
            mux,
            registry: None,
            stacks: StackManager::new(),
            bus: Arc::new(Mutex::new(EventBus::new())),
            layout: LayoutTree::default_layout(),
            surfaces: SurfaceRegistry::new(),
            pty: PtyManager::new(),
            session: None,
            dirty: false,
            cwd: String::new(),
        }
    }

    pub fn with_registry(mux: Box<dyn Mux>, ctx: SystemContext) -> Self {
        Self {
            mux,
            registry: Some(CapabilityRegistry::new(ctx)),
            stacks: StackManager::new(),
            bus: Arc::new(Mutex::new(EventBus::new())),
            layout: LayoutTree::default_layout(),
            surfaces: SurfaceRegistry::new(),
            pty: PtyManager::new(),
            session: None,
            dirty: false,
            cwd: String::new(),
        }
    }

    // -- Workspace -----------------------------------------------------------

    /// Initialize a workspace session on the mux.
    pub fn create_workspace(&mut self, name: &str, cwd: &str) -> String {
        let session = self.mux.initialize(name, cwd);
        self.session = Some(session.clone());
        self.cwd = cwd.to_string();
        self.bus.lock().unwrap().publish(
            TypedEvent::new(EventType::Custom, "workspace.created")
                .with_payload("name", name),
        );
        session
    }

    /// Current session handle.
    pub fn session(&self) -> Option<&str> {
        self.session.as_deref()
    }

    pub fn is_dirty(&self) -> bool {
        self.dirty
    }

    pub fn mark_dirty(&mut self) {
        self.dirty = true;
    }

    pub fn clear_dirty(&mut self) {
        self.dirty = false;
    }

    pub fn cwd(&self) -> &str {
        &self.cwd
    }

    /// Create a serializable snapshot of the current workspace state.
    pub fn snapshot(&self) -> WorkspaceSave {
        let panes: HashMap<String, PaneState> = self
            .layout
            .root
            .leaf_ids()
            .into_iter()
            .map(|id| {
                (
                    id,
                    PaneState {
                        cwd: Some(self.cwd.clone()),
                        command: None,
                        args: vec![],
                    },
                )
            })
            .collect();

        WorkspaceSave {
            version: 1,
            name: self.session.clone().unwrap_or_else(|| "unnamed".to_string()),
            cwd: self.cwd.clone(),
            timestamp: chrono::Utc::now().to_rfc3339(),
            layout: self.layout.clone(),
            panes,
            stacks: self.stacks.clone(),
        }
    }

    // -- Stack operations ----------------------------------------------------

    /// Route a stack operation through NexusCore.
    ///
    /// Operations: push, switch, replace, close, adopt, tag, untag, rename
    pub fn handle_stack_op(&mut self, op: &str, payload: &HashMap<String, String>) -> OpResult {
        match op {
            "push" => self.stack_push(payload),
            "switch" => self.stack_switch(payload),
            "replace" => self.stack_replace(payload),
            "close" => self.stack_close(payload),
            "adopt" => self.stack_adopt(payload),
            "tag" => self.stack_tag(payload),
            "untag" => self.stack_untag(payload),
            "rename" => self.stack_rename(payload),
            "list" => self.stack_list(payload),
            "prev" => self.stack_rotate(payload, -1),
            "next" => self.stack_rotate(payload, 1),
            _ => OpResult::error("unknown_op"),
        }
    }

    fn stack_push(&mut self, payload: &HashMap<String, String>) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");
        let new_pane_id = match payload.get("pane_id") {
            Some(id) => id.clone(),
            None => return OpResult::error("no_pane_id"),
        };
        let name = payload.get("name").map(|s| s.as_str()).unwrap_or("Shell");

        let focused_id = payload
            .get("focused_id")
            .cloned()
            .or_else(|| {
                self.session
                    .as_ref()
                    .and_then(|s| self.mux.get_focused(s))
            })
            .unwrap_or_default();

        let (sid, stack) = self.stacks.get_or_create_by_identity(
            identity,
            if focused_id.is_empty() {
                None
            } else {
                Some(&focused_id)
            },
        );
        let sid = sid.clone();

        // Tag with role
        if !identity.is_empty() && !identity.starts_with("stack_") && stack.role.is_none() {
            stack.role = Some(identity.to_string());
            if !focused_id.is_empty() {
                self.mux.set_tag(&focused_id, "nexus_role", identity);
            }
        }

        let visible_id = get_visible_container(
            self.stacks.get_stack(&sid).unwrap(),
            &focused_id,
        );

        // Mark existing tabs as background and snapshot geometry
        if let (Some(vis), Some(stack)) = (visible_id.as_ref(), self.stacks.get_stack_mut(&sid)) {
            let geo = self.mux.get_geometry(vis);
            for tab in &mut stack.tabs {
                tab.status = TabStatus::Background;
                tab.is_active = false;
                if tab.pane_handle.as_deref() == Some(vis) {
                    tab.geometry = geo.clone();
                }
            }
        }

        // Ghost-swap
        if let Some(ref vis) = visible_id {
            if !self.mux.swap_containers(vis, &new_pane_id) {
                return OpResult::error("swap_failed");
            }
        }

        self.mux.focus(&new_pane_id);

        let geo = visible_id
            .as_ref()
            .and_then(|_| self.mux.get_geometry(&new_pane_id));

        // Add new tab
        let new_tab = Tab::new(name)
            .with_handle(&new_pane_id)
            .with_status(TabStatus::Visible, true);
        let stack = self.stacks.get_stack_mut(&sid).unwrap();
        let mut tab = new_tab;
        tab.geometry = geo;
        stack.tabs.push(tab);
        stack.active_index = stack.tabs.len() - 1;

        self.mux.set_tag(&new_pane_id, "nexus_stack_id", &sid);

        self.bus.lock().unwrap().publish(
            TypedEvent::new(EventType::StackPush, "stack.push")
                .with_payload("stack_id", sid.as_str())
                .with_payload("pane", new_pane_id.as_str())
                .with_payload("name", name),
        );

        OpResult::ok_with("stack_id", sid)
    }

    fn stack_switch(&mut self, payload: &HashMap<String, String>) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");
        let index: usize = payload
            .get("index")
            .and_then(|s| s.parse().ok())
            .unwrap_or(0);

        // Resolve sid with immutable borrow, then release
        let sid = match self.stacks.get_by_identity(identity) {
            Some((sid, _)) => sid.to_string(),
            None => return OpResult::error("not_found"),
        };

        // Now work with the stack through sid
        let (target_id, visible_id) = {
            let stack = self.stacks.get_stack(&sid).unwrap();
            if index >= stack.tabs.len() {
                return OpResult::error("not_found");
            }
            let target = match stack.tabs[index].pane_handle.clone() {
                Some(id) => id,
                None => return OpResult::error("no_handle"),
            };
            let focused_id = payload
                .get("focused_id")
                .cloned()
                .or_else(|| {
                    self.session
                        .as_ref()
                        .and_then(|s| self.mux.get_focused(s))
                })
                .unwrap_or_default();
            let visible = get_visible_container(stack, &focused_id);
            (target, visible)
        };

        if visible_id.as_deref() == Some(target_id.as_str()) {
            return OpResult::ok();
        }

        let outgoing_geo = visible_id
            .as_ref()
            .and_then(|v| self.mux.get_geometry(v));

        if let Some(ref vis) = visible_id {
            if !self.mux.swap_containers(vis, &target_id) {
                return OpResult::error("swap_failed");
            }
        }

        self.mux.focus(&target_id);

        // Restore geometry
        let incoming_geo = self.stacks.get_stack(&sid).unwrap().tabs[index].geometry.clone();
        if let Some(ref geo) = incoming_geo {
            self.mux.set_geometry(&target_id, geo);
        }

        // Update statuses
        let stack = self.stacks.get_stack_mut(&sid).unwrap();
        for (i, tab) in stack.tabs.iter_mut().enumerate() {
            if Some(tab.pane_handle.as_deref()) == Some(visible_id.as_deref()) {
                tab.geometry = outgoing_geo.clone();
            }
            tab.status = if i == index {
                TabStatus::Visible
            } else {
                TabStatus::Background
            };
            tab.is_active = i == index;
        }
        stack.active_index = index;

        self.bus.lock().unwrap().publish(
            TypedEvent::new(EventType::StackSwitch, "stack.switch")
                .with_payload("stack_id", sid.as_str())
                .with_payload("pane", target_id.as_str())
                .with_payload("index", index as u64),
        );

        OpResult::ok()
    }

    fn stack_replace(&mut self, payload: &HashMap<String, String>) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");
        let new_pane_id = match payload.get("pane_id") {
            Some(id) => id.clone(),
            None => return OpResult::error("no_pane_id"),
        };
        let name = payload.get("name").map(|s| s.as_str()).unwrap_or("Shell");

        // Resolve sid with immutable borrow
        let sid = match self.stacks.get_by_identity(identity) {
            Some((sid, _)) => sid.to_string(),
            None => return self.stack_push(payload),
        };

        let (idx, old_pane_id, visible_id) = {
            let stack = self.stacks.get_stack(&sid).unwrap();
            let idx = stack.active_index;
            let old = stack.tabs[idx].pane_handle.clone();
            let focused_id = payload
                .get("focused_id")
                .cloned()
                .or_else(|| {
                    self.session
                        .as_ref()
                        .and_then(|s| self.mux.get_focused(s))
                })
                .unwrap_or_default();
            let visible = get_visible_container(stack, &focused_id);
            (idx, old, visible)
        };

        let geo = visible_id
            .as_ref()
            .and_then(|v| self.mux.get_geometry(v));

        if let Some(ref vis) = visible_id {
            if !self.mux.swap_containers(vis, &new_pane_id) {
                return OpResult::error("swap_failed");
            }
        }

        self.mux.focus(&new_pane_id);
        if let Some(ref g) = geo {
            self.mux.set_geometry(&new_pane_id, g);
        }

        // Kill old pane
        if let Some(ref old) = old_pane_id {
            if old != &new_pane_id {
                self.mux.destroy_container(old);
            }
        }

        // Replace tab in-place
        let mut new_tab = Tab::new(name)
            .with_handle(&new_pane_id)
            .with_status(TabStatus::Visible, true);
        new_tab.geometry = geo;
        let stack = self.stacks.get_stack_mut(&sid).unwrap();
        stack.tabs[idx] = new_tab;

        self.bus.lock().unwrap().publish(
            TypedEvent::new(EventType::StackReplace, "stack.replace")
                .with_payload("stack_id", sid.as_str())
                .with_payload("new_pane", new_pane_id.as_str()),
        );

        OpResult::ok()
    }

    fn stack_close(&mut self, payload: &HashMap<String, String>) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");

        // Resolve sid and extract data with immutable borrow
        let (sid, idx, target_id, foundation_id, visible_id) = {
            let (sid, stack) = match self.stacks.get_by_identity(identity) {
                Some((sid, stack)) => (sid.to_string(), stack),
                None => return OpResult::error("empty"),
            };

            if stack.tabs.is_empty() {
                return OpResult::error("empty");
            }

            let idx = stack.active_index;
            if idx == 0 {
                return OpResult::error("foundation_protected");
            }

            let target = stack.tabs[idx].pane_handle.clone();
            let foundation = match stack.tabs[0].pane_handle.clone() {
                Some(id) => id,
                None => return OpResult::error("no_foundation"),
            };

            let focused_id = payload
                .get("focused_id")
                .cloned()
                .or_else(|| {
                    self.session
                        .as_ref()
                        .and_then(|s| self.mux.get_focused(s))
                })
                .unwrap_or_default();

            let visible = get_visible_container(stack, &focused_id);
            (sid, idx, target, foundation, visible)
        };

        if let Some(ref vis) = visible_id {
            if !self.mux.swap_containers(vis, &foundation_id) {
                return OpResult::error("swap_failed");
            }
        }

        self.mux.focus(&foundation_id);

        if let Some(ref target) = target_id {
            self.mux.destroy_container(target);
        }

        let stack = self.stacks.get_stack_mut(&sid).unwrap();
        stack.tabs.remove(idx);
        stack.active_index = 0;
        for (i, tab) in stack.tabs.iter_mut().enumerate() {
            tab.status = if i == 0 {
                TabStatus::Visible
            } else {
                TabStatus::Background
            };
            tab.is_active = i == 0;
        }

        self.bus.lock().unwrap().publish(
            TypedEvent::new(EventType::StackClose, "stack.close")
                .with_payload("stack_id", sid.as_str()),
        );

        OpResult::ok()
    }

    fn stack_adopt(&mut self, payload: &HashMap<String, String>) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");
        let pane_id = match payload.get("pane_id") {
            Some(id) => id.clone(),
            None => return OpResult::error("no_pane_id"),
        };
        let name = payload.get("name").map(|s| s.as_str()).unwrap_or("Shell");

        let (sid, stack) = self
            .stacks
            .get_or_create_by_identity(identity, Some(&pane_id));
        let sid = sid.clone();

        for tab in &mut stack.tabs {
            if tab.pane_handle.as_deref() == Some(&pane_id) {
                tab.status = TabStatus::Visible;
                tab.name = name.to_string();
            }
        }

        self.mux.set_tag(&pane_id, "nexus_stack_id", &sid);
        if let Some(ref role) = stack.role.clone() {
            self.mux.set_tag(&pane_id, "nexus_role", role);
        }

        OpResult::ok_with("stack_id", sid)
    }

    fn stack_tag(&mut self, payload: &HashMap<String, String>) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");
        let tag = match payload.get("tag") {
            Some(t) => t.clone(),
            None => return OpResult::error("no_tag"),
        };

        match self.stacks.get_by_identity_mut(identity) {
            Some((sid, stack)) => {
                if !stack.tags.contains(&tag) {
                    stack.tags.push(tag);
                }
                OpResult::ok_with("stack_id", sid)
            }
            None => OpResult::error("not_found"),
        }
    }

    fn stack_untag(&mut self, payload: &HashMap<String, String>) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");
        let tag = payload.get("tag").cloned().unwrap_or_default();

        match self.stacks.get_by_identity_mut(identity) {
            Some((_sid, stack)) => {
                stack.tags.retain(|t| t != &tag);
                OpResult::ok()
            }
            None => OpResult::error("not_found"),
        }
    }

    fn stack_list(&self, payload: &HashMap<String, String>) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");
        match self.stacks.get_by_identity(identity) {
            Some((_sid, stack)) => {
                let tabs: Vec<serde_json::Value> = stack.tabs.iter().enumerate().map(|(i, tab)| {
                    serde_json::json!({
                        "index": i,
                        "name": tab.name,
                        "pane_handle": tab.pane_handle,
                        "is_active": tab.is_active,
                    })
                }).collect();
                OpResult::ok_with("tabs", serde_json::Value::Array(tabs))
            }
            None => OpResult::error("not_found"),
        }
    }

    fn stack_rotate(&mut self, payload: &HashMap<String, String>, direction: i32) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str())
            .unwrap_or_else(|| self.layout.focused.as_str());
        let (sid, _) = match self.stacks.get_by_identity(identity) {
            Some((sid, stack)) => (sid.to_string(), stack),
            None => return OpResult::error("not_found"),
        };
        match self.stacks.rotate(&sid, direction) {
            crate::stack_manager::StackOpResult::Ok(Some(tab)) => {
                OpResult::ok_with("active_tab", serde_json::json!({
                    "name": tab.name,
                    "pane_handle": tab.pane_handle,
                }))
            }
            crate::stack_manager::StackOpResult::Ok(None) => OpResult::ok(),
            _ => OpResult::error("not_found"),
        }
    }

    fn stack_rename(&mut self, payload: &HashMap<String, String>) -> OpResult {
        let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");
        let name = match payload.get("name") {
            Some(n) => n.clone(),
            None => return OpResult::error("no_name"),
        };

        match self.stacks.get_by_identity_mut(identity) {
            Some((_sid, stack)) => {
                stack.role = Some(name);
                OpResult::ok()
            }
            None => OpResult::error("not_found"),
        }
    }

    // -- Event Bus -----------------------------------------------------------

    pub fn publish(&mut self, source: &str, payload: HashMap<String, serde_json::Value>) {
        let mut event = TypedEvent::new(EventType::Custom, source);
        event.payload = payload;
        self.bus.lock().unwrap().publish(event);
    }

    // -- PTY -----------------------------------------------------------------

    pub fn pty_spawn(&mut self, pane_id: &str, cwd: Option<&str>) -> Result<(), String> {
        let cwd = cwd.unwrap_or("/tmp");
        self.pty.spawn(pane_id, cwd, self.bus.clone())
    }

    pub fn pty_spawn_cmd(
        &mut self,
        pane_id: &str,
        cwd: &str,
        program: &str,
        args: &[String],
    ) -> Result<(), String> {
        self.pty.spawn_cmd(pane_id, cwd, program, args, self.bus.clone())
    }

    pub fn pty_write(&mut self, pane_id: &str, data: &str) -> Result<(), String> {
        self.pty.write(pane_id, data)
    }

    pub fn pty_resize(&mut self, pane_id: &str, cols: u16, rows: u16) -> Result<(), String> {
        self.pty.resize(pane_id, cols, rows)
    }

    pub fn pty_kill(&mut self, pane_id: &str) -> Result<(), String> {
        self.pty.kill(pane_id)
    }

    // -- Chat ----------------------------------------------------------------

    pub fn chat_send(&mut self, pane_id: &str, message: &str, cwd: &str) -> Result<(), String> {
        let registry = self.registry.as_ref().ok_or("No capability registry")?;
        let chat = registry.best_chat().ok_or("No chat adapter available")?;

        let (tx, rx) = std::sync::mpsc::channel();
        chat.send_message(message, cwd, tx).map_err(|e| e.to_string())?;

        let bus = self.bus.clone();
        let pid = pane_id.to_string();
        std::thread::spawn(move || {
            use nexus_core::capability::ChatEvent;
            while let Ok(event) = rx.recv() {
                if let Ok(mut b) = bus.lock() {
                    match &event {
                        ChatEvent::Start { backend } => {
                            b.publish(
                                TypedEvent::new(EventType::Custom, "agent.start")
                                    .with_payload("paneId", pid.as_str())
                                    .with_payload("backend", backend.as_str()),
                            );
                        }
                        ChatEvent::Text { chunk } => {
                            b.publish(
                                TypedEvent::new(EventType::Custom, "agent.text")
                                    .with_payload("paneId", pid.as_str())
                                    .with_payload("text", chunk.as_str()),
                            );
                        }
                        ChatEvent::Done { exit_code, full_text } => {
                            b.publish(
                                TypedEvent::new(EventType::Custom, "agent.done")
                                    .with_payload("paneId", pid.as_str())
                                    .with_payload("exitCode", *exit_code as i64)
                                    .with_payload("fullText", full_text.as_str()),
                            );
                            return;
                        }
                        ChatEvent::Error { message } => {
                            b.publish(
                                TypedEvent::new(EventType::Custom, "agent.error")
                                    .with_payload("paneId", pid.as_str())
                                    .with_payload("message", message.as_str()),
                            );
                            return;
                        }
                    }
                }
            }
        });

        Ok(())
    }

    // -- Keymap --------------------------------------------------------------

    pub fn get_keymap(&self) -> Vec<nexus_core::keymap::KeyBinding> {
        nexus_core::keymap::default_keymap()
    }

    pub fn get_commands(&self) -> Vec<nexus_core::keymap::CommandEntry> {
        let mut cmds = nexus_core::keymap::default_commands();
        let km = self.get_keymap();
        nexus_core::keymap::merge_bindings(&mut cmds, &km);
        cmds
    }

    /// List all registered adapters with availability.
    pub fn capabilities_list(&self, type_filter: Option<&str>) -> serde_json::Value {
        match &self.registry {
            Some(reg) => reg.capabilities_list(type_filter),
            None => serde_json::json!([]),
        }
    }

    /// List active sessions.
    pub fn session_list(&self) -> Vec<serde_json::Value> {
        match &self.session {
            Some(name) => vec![serde_json::json!({"name": name})],
            None => vec![],
        }
    }

    /// Number of active PTY processes.
    pub fn active_pty_count(&self) -> usize {
        self.pty.active_count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::surface::NullMux;

    fn make_core() -> NexusCore {
        let mut core = NexusCore::new(Box::new(NullMux::new()));
        core.create_workspace("test", "/tmp");
        core
    }

    fn payload(pairs: &[(&str, &str)]) -> HashMap<String, String> {
        pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect()
    }

    #[test]
    fn dirty_flag_starts_clean() {
        let core = make_core();
        assert!(!core.is_dirty());
    }

    #[test]
    fn dirty_flag_set_and_clear() {
        let mut core = make_core();
        core.mark_dirty();
        assert!(core.is_dirty());
        core.clear_dirty();
        assert!(!core.is_dirty());
    }

    #[test]
    fn snapshot_captures_state() {
        let core = make_core();
        let snap = core.snapshot();
        assert_eq!(snap.version, 1);
        assert_eq!(snap.layout.root.leaf_ids().len(), 4);
        assert_eq!(snap.cwd, "/tmp");
    }

    #[test]
    fn cwd_tracked_on_core() {
        let core = make_core();
        assert_eq!(core.cwd(), "/tmp");
    }

    #[test]
    fn create_workspace() {
        let mut core = NexusCore::new(Box::new(NullMux::new()));
        let session = core.create_workspace("test", "/tmp");
        assert_eq!(session, "null:test");
        assert_eq!(core.session(), Some("null:test"));
    }

    #[test]
    fn stack_push_creates_stack() {
        let mut core = make_core();
        let result = core.handle_stack_op(
            "push",
            &payload(&[("identity", "editor"), ("pane_id", "p1"), ("name", "Vim")]),
        );
        assert_eq!(result.status, "ok");
        assert!(result.data.contains_key("stack_id"));
    }

    #[test]
    fn stack_push_no_pane_id_errors() {
        let mut core = make_core();
        let result = core.handle_stack_op(
            "push",
            &payload(&[("identity", "editor")]),
        );
        assert_eq!(result.status, "error");
    }

    #[test]
    fn stack_adopt() {
        let mut core = make_core();
        let result = core.handle_stack_op(
            "adopt",
            &payload(&[("identity", "terminal"), ("pane_id", "p1"), ("name", "zsh")]),
        );
        assert_eq!(result.status, "ok");
    }

    #[test]
    fn stack_close_protects_foundation() {
        let mut core = make_core();
        // Push initial tab
        core.handle_stack_op(
            "push",
            &payload(&[("identity", "editor"), ("pane_id", "p1")]),
        );
        // Try to close foundation
        let result = core.handle_stack_op(
            "close",
            &payload(&[("identity", "editor")]),
        );
        assert_eq!(result.status, "error");
    }

    #[test]
    fn stack_tag_and_untag() {
        let mut core = make_core();
        core.handle_stack_op(
            "push",
            &payload(&[("identity", "editor"), ("pane_id", "p1")]),
        );

        let result = core.handle_stack_op(
            "tag",
            &payload(&[("identity", "editor"), ("tag", "important")]),
        );
        assert_eq!(result.status, "ok");

        let result = core.handle_stack_op(
            "untag",
            &payload(&[("identity", "editor"), ("tag", "important")]),
        );
        assert_eq!(result.status, "ok");
    }

    #[test]
    fn stack_rename() {
        let mut core = make_core();
        core.handle_stack_op(
            "push",
            &payload(&[("identity", "editor"), ("pane_id", "p1")]),
        );

        let result = core.handle_stack_op(
            "rename",
            &payload(&[("identity", "editor"), ("name", "code")]),
        );
        assert_eq!(result.status, "ok");
    }

    #[test]
    fn unknown_op_errors() {
        let mut core = make_core();
        let result = core.handle_stack_op("bogus", &HashMap::new());
        assert_eq!(result.status, "error");
    }

    #[test]
    fn with_registry_constructor() {
        let ctx = nexus_core::capability::SystemContext {
            path: String::new(),
            shell: String::new(),
        };
        let core = NexusCore::with_registry(Box::new(NullMux::new()), ctx);
        assert!(core.session().is_none());
    }

    #[test]
    fn pty_spawn_on_core() {
        let ctx = nexus_core::capability::SystemContext {
            path: std::env::var("PATH").unwrap_or_default(),
            shell: "/bin/zsh".into(),
        };
        let mut core = NexusCore::with_registry(Box::new(NullMux::new()), ctx);
        let result = core.pty_spawn("test-pane", None);
        assert!(result.is_ok());
        let _ = core.pty_kill("test-pane");
    }

    #[test]
    fn pty_write_nonexistent_errors() {
        let ctx = nexus_core::capability::SystemContext {
            path: String::new(),
            shell: String::new(),
        };
        let mut core = NexusCore::with_registry(Box::new(NullMux::new()), ctx);
        assert!(core.pty_write("nonexistent", "hello").is_err());
    }
}
