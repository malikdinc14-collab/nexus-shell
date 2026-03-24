//! Surface abstraction — the display/control layer for Nexus Shell.
//!
//! A Surface is anything that can host workspaces: a terminal multiplexer,
//! a tiling window manager, a desktop app, or a web browser. The core
//! never calls tmux, i3, or any display technology directly — it talks
//! to a Surface.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Supporting types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SplitDirection {
    Horizontal,
    Vertical,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Dimensions {
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Geometry {
    pub x: i32,
    pub y: i32,
    pub w: u32,
    pub h: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContainerInfo {
    pub handle: String,
    pub index: usize,
    pub width: u32,
    pub height: u32,
    pub x: i32,
    pub y: i32,
    pub command: String,
    pub title: String,
    pub focused: bool,
    pub tags: HashMap<String, String>,
}

impl Default for ContainerInfo {
    fn default() -> Self {
        Self {
            handle: String::new(),
            index: 0,
            width: 80,
            height: 24,
            x: 0,
            y: 0,
            command: String::new(),
            title: String::new(),
            focused: false,
            tags: HashMap::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MenuItem {
    pub id: String,
    pub label: String,
    pub icon: Option<String>,
    pub description: Option<String>,
    pub value: Option<String>,
    pub depth: usize,
    pub has_children: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HudModule {
    pub id: String,
    pub label: String,
    pub value: String,
    pub position: String,
    pub color: Option<String>,
}

// ---------------------------------------------------------------------------
// Surface trait
// ---------------------------------------------------------------------------

/// Abstract base for all display surfaces.
///
/// A Surface handles spatial layout, process attachment, menu rendering,
/// HUD display, and notifications. The core calls Surface methods;
/// implementations translate to tmux, Sway, Tauri IPC, WebSocket, etc.
pub trait Surface: Send + Sync {
    // -- Lifecycle -----------------------------------------------------------

    /// Create or attach to a workspace session. Returns session handle.
    fn initialize(&mut self, session_name: &str, cwd: &str) -> String;

    /// Destroy a workspace session and all its containers.
    fn teardown(&mut self, session: &str);

    // -- Spatial — container management --------------------------------------

    /// Create a new container in the session. Returns container handle.
    fn create_container(&mut self, session: &str, command: &str, cwd: &str) -> String;

    /// Split a container. Returns new container handle.
    fn split(
        &mut self,
        handle: &str,
        direction: SplitDirection,
        size: Option<u32>,
        cwd: &str,
    ) -> String;

    /// Destroy a container and its contents.
    fn destroy_container(&mut self, handle: &str);

    /// Move focus to a container.
    fn focus(&mut self, handle: &str);

    /// Resize a container.
    fn resize(&mut self, handle: &str, dimensions: Dimensions);

    // -- Swap — atomic container exchange ------------------------------------

    /// Atomically swap two containers (ghost-swap).
    fn swap_containers(&mut self, source: &str, target: &str) -> bool;

    /// Return true if the container handle is still alive.
    fn container_exists(&self, handle: &str) -> bool;

    // -- Content — process management ----------------------------------------

    /// Run a command inside a container.
    fn attach_process(&mut self, handle: &str, command: &str);

    /// Send keystrokes to a container.
    fn send_input(&mut self, handle: &str, keys: &str);

    // -- State — query containers --------------------------------------------

    /// Return all containers in the session.
    fn list_containers(&self, session: &str) -> Vec<ContainerInfo>;

    /// Return the handle of the currently focused container.
    fn get_focused(&self, session: &str) -> Option<String>;

    /// Return dimensions of a container.
    fn get_dimensions(&self, handle: &str) -> Dimensions;

    /// Return full geometry of a container.
    fn get_geometry(&self, handle: &str) -> Option<Geometry>;

    /// Apply geometry to a container.
    fn set_geometry(&mut self, handle: &str, geometry: &Geometry);

    // -- Metadata — tag containers -------------------------------------------

    /// Attach metadata to a container.
    fn set_tag(&mut self, handle: &str, key: &str, value: &str);

    /// Retrieve metadata from a container.
    fn get_tag(&self, handle: &str, key: &str) -> String;

    /// Set the display title of a container.
    fn set_title(&mut self, handle: &str, title: &str);

    // -- Rendering — menus, HUD, notifications -------------------------------

    /// Display a menu and return the selected item ID.
    fn show_menu(&mut self, items: &[MenuItem], prompt: &str) -> Option<String>;

    /// Update the HUD/status display.
    fn show_hud(&mut self, modules: &[HudModule]);

    /// Show a notification to the user.
    fn notify(&mut self, message: &str, level: &str);

    // -- Layout --------------------------------------------------------------

    /// Apply a composition layout to the session.
    fn apply_layout(&mut self, session: &str, layout: &serde_json::Value) -> bool;

    /// Capture the current layout for persistence.
    fn capture_layout(&self, session: &str) -> serde_json::Value;

    // -- Environment ---------------------------------------------------------

    /// Set an environment variable visible to all containers.
    fn set_env(&mut self, session: &str, key: &str, value: &str);
}

// ---------------------------------------------------------------------------
// NullSurface — no-op implementation for testing
// ---------------------------------------------------------------------------

/// No-op surface for testing and headless operation.
pub struct NullSurface {
    counter: u64,
    tags: HashMap<(String, String), String>,
}

impl NullSurface {
    pub fn new() -> Self {
        Self {
            counter: 0,
            tags: HashMap::new(),
        }
    }

    fn next_id(&mut self) -> String {
        self.counter += 1;
        format!("null:{}", self.counter)
    }
}

impl Default for NullSurface {
    fn default() -> Self {
        Self::new()
    }
}

impl Surface for NullSurface {
    fn initialize(&mut self, session_name: &str, _cwd: &str) -> String {
        format!("null:{session_name}")
    }

    fn teardown(&mut self, _session: &str) {}

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
        true
    }

    fn container_exists(&self, _handle: &str) -> bool {
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

    fn show_menu(&mut self, _items: &[MenuItem], _prompt: &str) -> Option<String> {
        None
    }

    fn show_hud(&mut self, _modules: &[HudModule]) {}

    fn notify(&mut self, _message: &str, _level: &str) {}

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
    fn null_surface_initialize() {
        let mut s = NullSurface::new();
        let handle = s.initialize("test", "/tmp");
        assert_eq!(handle, "null:test");
    }

    #[test]
    fn null_surface_create_container_increments() {
        let mut s = NullSurface::new();
        let a = s.create_container("sess", "", "");
        let b = s.create_container("sess", "", "");
        assert_ne!(a, b);
    }

    #[test]
    fn null_surface_tags_roundtrip() {
        let mut s = NullSurface::new();
        s.set_tag("pane1", "role", "editor");
        assert_eq!(s.get_tag("pane1", "role"), "editor");
        assert_eq!(s.get_tag("pane1", "missing"), "");
    }

    #[test]
    fn null_surface_swap_always_succeeds() {
        let mut s = NullSurface::new();
        assert!(s.swap_containers("a", "b"));
    }
}
