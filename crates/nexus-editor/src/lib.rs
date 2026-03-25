//! Editor adapters — implement EditorCapability from nexus-core.
//!
//! Implementations: NullEditor (no-op), NeovimAdapter (future).

use std::collections::HashMap;

use nexus_core::capability::{
    AdapterManifest, Capability, CapabilityType, EditorCapability,
};
use nexus_core::NexusError;

/// No-op editor for testing and headless operation.
pub struct NullEditor;

impl Capability for NullEditor {
    fn manifest(&self) -> &AdapterManifest {
        static MANIFEST: AdapterManifest = AdapterManifest {
            name: "null",
            capability_type: CapabilityType::Editor,
            priority: 0,
            binary: "",
        };
        &MANIFEST
    }

    fn is_available(&self) -> bool {
        false // Null editor is never "available" — it's the fallback
    }
}

impl EditorCapability for NullEditor {
    fn open(&mut self, _path: &str, _line: u32, _col: u32) -> Result<(), NexusError> {
        Ok(())
    }

    fn get_current_buffer(&self) -> Option<String> {
        None
    }

    fn get_buffer_content(&self, _max_lines: u32) -> Option<String> {
        None
    }

    fn apply_edit(&mut self, _patch: &str) -> Result<(), NexusError> {
        Ok(())
    }

    fn get_tabs(&self) -> Vec<HashMap<String, String>> {
        Vec::new()
    }

    fn send_command(&mut self, _cmd: &str) -> Result<(), NexusError> {
        Ok(())
    }

    fn remote_expr(&self, _expr: &str) -> Option<String> {
        None
    }

    fn is_alive(&self) -> bool {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use nexus_core::capability::Capability;

    #[test]
    fn null_editor_manifest() {
        let ed = NullEditor;
        let m = ed.manifest();
        assert_eq!(m.name, "null");
        assert_eq!(m.capability_type, CapabilityType::Editor);
    }

    #[test]
    fn null_editor_not_available() {
        let ed = NullEditor;
        assert!(!ed.is_available());
    }

    #[test]
    fn null_editor_open_returns_ok() {
        let mut ed = NullEditor;
        assert!(ed.open("/tmp/foo.rs", 0, 0).is_ok());
    }

    #[test]
    fn null_editor_is_alive_false() {
        let ed = NullEditor;
        assert!(!ed.is_alive());
    }

    #[test]
    fn null_editor_is_send_sync() {
        fn assert_send_sync<T: Send + Sync>() {}
        assert_send_sync::<NullEditor>();
    }

    #[test]
    fn null_editor_get_tabs_empty() {
        let ed = NullEditor;
        assert!(ed.get_tabs().is_empty());
    }

    #[test]
    fn null_editor_apply_edit_ok() {
        let mut ed = NullEditor;
        assert!(ed.apply_edit("patch").is_ok());
    }
}
