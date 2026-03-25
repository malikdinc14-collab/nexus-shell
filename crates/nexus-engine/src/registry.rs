//! CapabilityRegistry — priority-ranked adapter discovery.
//!
//! The embedding binary (Tauri or daemon) constructs adapters and registers
//! them at startup. `best_*()` returns the highest-priority available adapter,
//! enabling graceful fallback when a preferred backend is absent.

use nexus_core::capability::{
    Capability, ChatCapability, EditorCapability, ExplorerCapability, SystemContext,
};

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

pub struct CapabilityRegistry {
    chat: Vec<Box<dyn ChatCapability>>,
    editor: Vec<Box<dyn EditorCapability>>,
    explorer: Vec<Box<dyn ExplorerCapability>>,
    pub ctx: SystemContext,
}

impl CapabilityRegistry {
    /// Create an empty registry bound to the given system context.
    pub fn new(ctx: SystemContext) -> Self {
        Self {
            chat: Vec::new(),
            editor: Vec::new(),
            explorer: Vec::new(),
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
        self.explorer.push(adapter);
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
        best_of(self.explorer.iter().map(|a| a.as_ref() as &dyn ExplorerCapability))
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
        &self.explorer
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
}
