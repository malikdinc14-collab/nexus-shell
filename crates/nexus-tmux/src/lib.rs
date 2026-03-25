//! TmuxMux — stub implementation of the Mux trait for tmux.
//!
//! Phase 3: all methods are no-ops or return placeholder values.
//! Phase 8: replace stubs with real tmux IPC calls.

use nexus_core::mux::{ContainerInfo, Dimensions, Geometry, Mux, SplitDirection};
use std::collections::HashMap;

/// Nexus Mux adapter for tmux.
///
/// Phase 3 stub — non-functional. All methods will be replaced in Phase 8
/// with real tmux IPC calls via `tmux display-message`, `split-window`, etc.
pub struct TmuxMux {
    session: Option<String>,
    counter: u64,
    tags: HashMap<(String, String), String>,
}

impl TmuxMux {
    pub fn new() -> Self {
        Self {
            session: None,
            counter: 0,
            tags: HashMap::new(),
        }
    }

    fn next_id(&mut self) -> String {
        self.counter += 1;
        format!("tmux:{}", self.counter)
    }
}

impl Default for TmuxMux {
    fn default() -> Self {
        Self::new()
    }
}

impl Mux for TmuxMux {
    fn initialize(&mut self, session_name: &str, _cwd: &str) -> String {
        let handle = format!("tmux:{session_name}");
        self.session = Some(handle.clone());
        handle
    }

    fn teardown(&mut self, _session: &str) {
        self.session = None;
    }

    fn create_container(&mut self, _session: &str, _command: &str, _cwd: &str) -> String {
        self.next_id()
    }

    fn split(
        &mut self,
        _handle: &str,
        _direction: SplitDirection,
        _size: Option<u32>,
        _cwd: &str,
    ) -> String {
        self.next_id()
    }

    fn destroy_container(&mut self, _handle: &str) {}

    fn focus(&mut self, _handle: &str) {}

    fn resize(&mut self, _handle: &str, _dimensions: Dimensions) {}

    fn swap_containers(&mut self, _source: &str, _target: &str) -> bool {
        // Stub: always succeeds. Real impl: tmux swap-pane.
        true
    }

    fn container_exists(&self, _handle: &str) -> bool {
        // Stub: always true. Real impl: check tmux pane list.
        true
    }

    fn attach_process(&mut self, _handle: &str, _command: &str) {}

    fn send_input(&mut self, _handle: &str, _keys: &str) {}

    fn list_containers(&self, _session: &str) -> Vec<ContainerInfo> {
        Vec::new()
    }

    fn get_focused(&self, _session: &str) -> Option<String> {
        None
    }

    fn get_dimensions(&self, _handle: &str) -> Dimensions {
        Dimensions {
            width: 80,
            height: 24,
        }
    }

    fn get_geometry(&self, _handle: &str) -> Option<Geometry> {
        Some(Geometry {
            x: 0,
            y: 0,
            w: 80,
            h: 24,
        })
    }

    fn set_geometry(&mut self, _handle: &str, _geometry: &Geometry) {}

    fn set_tag(&mut self, handle: &str, key: &str, value: &str) {
        self.tags
            .insert((handle.to_string(), key.to_string()), value.to_string());
    }

    fn get_tag(&self, handle: &str, key: &str) -> String {
        self.tags
            .get(&(handle.to_string(), key.to_string()))
            .cloned()
            .unwrap_or_default()
    }

    fn set_title(&mut self, _handle: &str, _title: &str) {}

    fn apply_layout(&mut self, _session: &str, _layout: &serde_json::Value) -> bool {
        false
    }

    fn capture_layout(&self, _session: &str) -> serde_json::Value {
        serde_json::Value::Object(serde_json::Map::new())
    }

    fn set_env(&mut self, _session: &str, _key: &str, _value: &str) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tmux_mux_implements_mux() {
        fn assert_mux<T: Mux>() {}
        assert_mux::<TmuxMux>();
    }

    #[test]
    fn tmux_mux_initialize_returns_session_name() {
        let mut mux = TmuxMux::new();
        let session = mux.initialize("test", "/tmp");
        assert!(!session.is_empty());
        assert!(session.contains("test"));
    }

    #[test]
    fn tmux_mux_tags_roundtrip() {
        let mut mux = TmuxMux::new();
        mux.set_tag("pane1", "role", "editor");
        assert_eq!(mux.get_tag("pane1", "role"), "editor");
        assert_eq!(mux.get_tag("pane1", "missing"), "");
    }

    #[test]
    fn tmux_mux_counter_increments() {
        let mut mux = TmuxMux::new();
        let a = mux.create_container("sess", "", "");
        let b = mux.create_container("sess", "", "");
        assert_ne!(a, b);
    }
}
