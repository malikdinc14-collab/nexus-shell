//! CapabilityRegistry — priority-ranked adapter discovery.
//!
//! The embedding binary (Tauri or daemon) constructs adapters and registers
//! them at startup. `best_*()` returns the highest-priority available adapter,
//! enabling graceful fallback when a preferred backend is absent.

use nexus_core::capability::{
    Capability, CapabilityType, ChatCapability, EditorCapability, ExplorerCapability,
    BrowserCapability, RichTextCapability, HUDCapability, SystemContext,
};

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

pub struct CapabilityRegistry {
    chat: Vec<Box<dyn ChatCapability>>,
    editor: Vec<Box<dyn EditorCapability>>,
    pub explorers: Vec<Box<dyn ExplorerCapability>>,
    pub browsers: Vec<Box<dyn BrowserCapability>>,
    pub richtext: Vec<Box<dyn RichTextCapability>>,
    pub huds: Vec<Box<dyn HUDCapability>>,
    pub ctx: SystemContext,
}

impl CapabilityRegistry {
    /// Create an empty registry bound to the given system context.
    pub fn new(ctx: SystemContext) -> Self {
        Self {
            chat: Vec::new(),
            editor: Vec::new(),
            explorers: Vec::new(),
            browsers: Vec::new(),
            richtext: Vec::new(),
            huds: Vec::new(),
            ctx,
        }
    }

    // -----------------------------------------------------------------------
    // Registration
    // -----------------------------------------------------------------------

    pub fn register_chat(&mut self, adapter: Box<dyn ChatCapability>) {
        self.chat.push(adapter);
    }

    pub fn register_editor(&mut self, adapter: Box<dyn EditorCapability>) {
        self.editor.push(adapter);
    }

    pub fn register_explorer(&mut self, adapter: Box<dyn ExplorerCapability>) {
        self.explorers.push(adapter);
    }
    pub fn register_browser(&mut self, adapter: Box<dyn BrowserCapability>) {
        self.browsers.push(adapter);
    }

    pub fn register_richtext(&mut self, adapter: Box<dyn RichTextCapability>) {
        self.richtext.push(adapter);
    }

    pub fn register_hud(&mut self, adapter: Box<dyn HUDCapability>) {
        self.huds.push(adapter);
    }

    // -----------------------------------------------------------------------
    // Best-available queries
    // -----------------------------------------------------------------------

    /// Return the highest-priority available chat adapter, or `None`.
    pub fn best_chat(&self) -> Option<&dyn ChatCapability> {
        best_of(self.chat.iter().map(|a| a.as_ref() as &dyn ChatCapability))
    }

    /// Return the highest-priority available editor adapter, or `None`.
    pub fn best_editor(&self) -> Option<&dyn EditorCapability> {
        best_of(self.editor.iter().map(|a| a.as_ref() as &dyn EditorCapability))
    }

    /// Return the highest-priority available explorer adapter, or `None`.
    pub fn best_explorer(&self) -> Option<&dyn ExplorerCapability> {
        best_of(self.explorers.iter().map(|a| a.as_ref() as &dyn ExplorerCapability))
    }
    pub fn best_browser(&self) -> Option<&dyn BrowserCapability> {
        best_of(self.browsers.iter().map(|a| a.as_ref() as &dyn BrowserCapability))
    }

    pub fn best_richtext(&self) -> Option<&dyn RichTextCapability> {
        best_of(self.richtext.iter().map(|a| a.as_ref() as &dyn RichTextCapability))
    }

    pub fn best_hud(&self) -> Option<&dyn HUDCapability> {
        best_of(self.huds.iter().map(|a| a.as_ref() as &dyn HUDCapability))
    }

    // -----------------------------------------------------------------------
    // Full-list accessors
    // -----------------------------------------------------------------------

    pub fn list_chat(&self) -> &[Box<dyn ChatCapability>] {
        &self.chat
    }

    pub fn list_editor(&self) -> &[Box<dyn EditorCapability>] {
        &self.editor
    }

    pub fn list_explorer(&self) -> &[Box<dyn ExplorerCapability>] {
        &self.explorers
    }
    pub fn list_browser(&self) -> &[Box<dyn BrowserCapability>] {
        &self.browsers
    }

    /// Return all registered adapters as JSON, optionally filtered by type.
    pub fn capabilities_list(&self, type_filter: Option<&str>) -> serde_json::Value {
        let mut result = Vec::new();
        let add = |result: &mut Vec<serde_json::Value>, cap: &dyn Capability| {
            let m = cap.manifest();
            result.push(serde_json::json!({
                "name": m.name,
                "type": match m.capability_type {
                    CapabilityType::Chat => "chat",
                    CapabilityType::Editor => "editor",
                    CapabilityType::Explorer => "explorer",
                    CapabilityType::Browser => "browser",
                    CapabilityType::Multiplexer => "multiplexer",
                    CapabilityType::RichText => "richtext",
                    CapabilityType::HUD => "hud",
                },
                "priority": m.priority,
                "binary": m.binary,
                "available": cap.is_available(),
            }));
        };

        if type_filter.is_none() || type_filter == Some("chat") {
            for c in &self.chat {
                add(&mut result, c.as_ref());
            }
        }
        if type_filter.is_none() || type_filter == Some("editor") {
            for c in &self.editor {
                add(&mut result, c.as_ref());
            }
        }
        if type_filter.is_none() || type_filter == Some("explorer") {
            for c in &self.explorers {
                add(&mut result, c.as_ref() as &dyn Capability);
            }
        }
        if type_filter.is_none() || type_filter == Some("browser") {
            for c in &self.browsers {
                add(&mut result, c.as_ref() as &dyn Capability);
            }
        }

        serde_json::Value::Array(result)
    }
}

// ---------------------------------------------------------------------------
// Internal helper
// ---------------------------------------------------------------------------

/// Filter available adapters and return the one with the highest priority.
fn best_of<'a, T>(iter: impl Iterator<Item = &'a T>) -> Option<&'a T>
where
    T: Capability + ?Sized,
{
    iter.filter(|a| a.is_available())
        .max_by_key(|a| a.manifest().priority)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use nexus_core::capability::*;

    struct StubChat {
        manifest: AdapterManifest,
        available: bool,
    }

    impl StubChat {
        fn new(name: &'static str, priority: u32, available: bool) -> Self {
            Self {
                manifest: AdapterManifest {
                    name,
                    capability_type: CapabilityType::Chat,
                    priority,
                    binary: "stub",
                },
                available,
            }
        }
    }

    impl Capability for StubChat {
        fn manifest(&self) -> &AdapterManifest {
            &self.manifest
        }
        fn is_available(&self) -> bool {
            self.available
        }
    }

    impl ChatCapability for StubChat {
        fn send_message(
            &self,
            _: &str,
            _: &str,
            _: std::sync::mpsc::Sender<ChatEvent>,
        ) -> Result<(), nexus_core::NexusError> {
            Ok(())
        }
        fn get_launch_command(&self) -> Option<String> {
            None
        }
    }

    struct StubExplorer {
        manifest: AdapterManifest,
    }

    impl Capability for StubExplorer {
        fn manifest(&self) -> &AdapterManifest {
            &self.manifest
        }
        fn is_available(&self) -> bool {
            true
        }
    }

    impl ExplorerCapability for StubExplorer {
        fn list_directory(&self, _: &str) -> Result<Vec<DirEntry>, nexus_core::NexusError> {
            Ok(vec![])
        }
        fn get_selection(&self) -> Option<String> {
            None
        }
        fn trigger_action(
            &mut self,
            _: &str,
            _: &str,
        ) -> Result<(), nexus_core::NexusError> {
            Ok(())
        }
        fn get_launch_command(&self) -> Option<String> {
            None
        }
    }

    fn empty_ctx() -> SystemContext {
        SystemContext {
            path: String::new(),
            shell: String::new(),
        }
    }

    #[test]
    fn empty_registry_returns_none() {
        let reg = CapabilityRegistry::new(empty_ctx());
        assert!(reg.best_chat().is_none());
        assert!(reg.best_explorer().is_none());
    }

    #[test]
    fn best_chat_returns_highest_priority_available() {
        let mut reg = CapabilityRegistry::new(empty_ctx());
        reg.register_chat(Box::new(StubChat::new("low", 50, true)));
        reg.register_chat(Box::new(StubChat::new("high", 100, true)));
        reg.register_chat(Box::new(StubChat::new("highest_unavailable", 200, false)));
        let best = reg.best_chat().unwrap();
        assert_eq!(best.manifest().name, "high");
    }

    #[test]
    fn best_chat_skips_unavailable() {
        let mut reg = CapabilityRegistry::new(empty_ctx());
        reg.register_chat(Box::new(StubChat::new("unavailable", 100, false)));
        assert!(reg.best_chat().is_none());
    }

    #[test]
    fn list_chat_returns_all() {
        let mut reg = CapabilityRegistry::new(empty_ctx());
        reg.register_chat(Box::new(StubChat::new("a", 50, true)));
        reg.register_chat(Box::new(StubChat::new("b", 100, false)));
        assert_eq!(reg.list_chat().len(), 2);
    }

    #[test]
    fn register_explorer() {
        let mut reg = CapabilityRegistry::new(empty_ctx());
        reg.register_explorer(Box::new(StubExplorer {
            manifest: AdapterManifest {
                name: "fs",
                capability_type: CapabilityType::Explorer,
                priority: 50,
                binary: "",
            },
        }));
        assert!(reg.best_explorer().is_some());
    }

    #[test]
    fn capabilities_list_all() {
        let mut reg = CapabilityRegistry::new(empty_ctx());
        reg.register_chat(Box::new(StubChat::new("claude", 100, true)));
        let list = reg.capabilities_list(None);
        let arr = list.as_array().unwrap();
        assert_eq!(arr.len(), 1);
        assert_eq!(arr[0]["name"], "claude");
        assert_eq!(arr[0]["available"], true);
    }

    #[test]
    fn capabilities_list_filtered() {
        let mut reg = CapabilityRegistry::new(empty_ctx());
        reg.register_chat(Box::new(StubChat::new("claude", 100, true)));
        reg.register_explorer(Box::new(StubExplorer {
            manifest: AdapterManifest {
                name: "fs",
                capability_type: CapabilityType::Explorer,
                priority: 50,
                binary: "",
            },
        }));
        let chat_only = reg.capabilities_list(Some("chat"));
        assert_eq!(chat_only.as_array().unwrap().len(), 1);
        let explorer_only = reg.capabilities_list(Some("explorer"));
        assert_eq!(explorer_only.as_array().unwrap().len(), 1);
    }
}
