//! Surface ABC — types for surface registration and capability declaration.
//!
//! Every surface (tmux, Tauri, web, CLI) registers with the engine, declaring
//! its mode and capabilities. The engine adapts behavior accordingly.
//!
//! See `.gap/specs/surface-abc.md` for the full design spec.

use serde::{Deserialize, Serialize};

/// How a surface renders panes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SurfaceMode {
    /// Engine drives physical layout via Mux trait (tmux, sway).
    Delegated,
    /// Surface renders from engine state events (Tauri, web, Android).
    Internal,
    /// No rendering. State access only (CLI, tests, scripting).
    Headless,
}

/// What a surface can do. The engine and menu system adapt based on these flags.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceCapabilities {
    // -- Rendering --
    /// Can show floating overlays (tmux display-popup, Tauri dialog).
    #[serde(default)]
    pub popup: bool,
    /// Can render menu/command palette (fzf, gum, cmdk).
    #[serde(default)]
    pub menu: bool,
    /// Can show persistent status bar (tmux status-line, Tauri bar).
    #[serde(default)]
    pub hud: bool,
    /// Can show toasts/alerts (tmux display-message, OS notification).
    #[serde(default)]
    pub notifications: bool,
    /// Can render HTML/markdown/images (Tauri webview, web — NOT tmux).
    #[serde(default)]
    pub rich_content: bool,

    // -- Layout --
    /// Surface does its own tiling (Tauri, web).
    #[serde(default)]
    pub internal_tiling: bool,
    /// Surface delegates tiling to backend (tmux, sway).
    #[serde(default)]
    pub external_tiling: bool,
    /// Panes can become OS windows (Tauri, sway).
    #[serde(default)]
    pub detachable_panes: bool,
    /// Surface supports transparent backgrounds (Tauri, compositor).
    #[serde(default)]
    pub transparency: bool,
    /// Surface supports gaps between panes (Tauri desktop mode).
    #[serde(default)]
    pub gaps: bool,
    /// Surface supports multiple OS windows / monitors.
    #[serde(default)]
    pub multi_window: bool,

    // -- Input --
    /// Can receive keyboard events.
    #[serde(default)]
    pub keyboard: bool,
    /// Can receive mouse events.
    #[serde(default)]
    pub mouse: bool,
    /// Touchscreen input (Android, iPad).
    #[serde(default)]
    pub touch: bool,

    // -- Lifecycle --
    /// Survives client disconnect (tmux, daemon mode).
    #[serde(default)]
    pub persistent: bool,
    /// Multiple clients can attach simultaneously.
    #[serde(default)]
    pub multi_client: bool,
    /// Supports reconnect with state reconciliation.
    #[serde(default)]
    pub reconnectable: bool,
}

impl Default for SurfaceCapabilities {
    fn default() -> Self {
        Self {
            popup: false,
            menu: false,
            hud: false,
            notifications: false,
            rich_content: false,
            internal_tiling: false,
            external_tiling: false,
            detachable_panes: false,
            transparency: false,
            gaps: false,
            multi_window: false,
            keyboard: true,
            mouse: false,
            touch: false,
            persistent: false,
            multi_client: false,
            reconnectable: false,
        }
    }
}

/// A connected surface tracked by the engine.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceRegistration {
    /// Unique identifier (e.g. "tauri-main", "tmux-0").
    pub id: String,
    /// Human-readable name (e.g. "Tauri Desktop", "tmux").
    pub name: String,
    /// Rendering mode.
    pub mode: SurfaceMode,
    /// Declared capabilities.
    pub capabilities: SurfaceCapabilities,
}

/// Manages connected surfaces.
#[derive(Debug, Default)]
pub struct SurfaceRegistry {
    surfaces: Vec<SurfaceRegistration>,
}

impl SurfaceRegistry {
    pub fn new() -> Self {
        Self { surfaces: Vec::new() }
    }

    /// Register a surface. Returns error if a second Delegated surface is attempted.
    pub fn register(&mut self, reg: SurfaceRegistration) -> Result<(), String> {
        if reg.mode == SurfaceMode::Delegated && self.has_delegated() {
            return Err("only one Delegated surface allowed at a time".into());
        }
        // Replace if same id reconnects
        self.surfaces.retain(|s| s.id != reg.id);
        self.surfaces.push(reg);
        Ok(())
    }

    /// Unregister a surface by id.
    pub fn unregister(&mut self, id: &str) -> bool {
        let before = self.surfaces.len();
        self.surfaces.retain(|s| s.id != id);
        self.surfaces.len() < before
    }

    /// List all registered surfaces.
    pub fn list(&self) -> &[SurfaceRegistration] {
        &self.surfaces
    }

    /// Check if any Delegated surface is registered.
    pub fn has_delegated(&self) -> bool {
        self.surfaces.iter().any(|s| s.mode == SurfaceMode::Delegated)
    }

    /// Get the active surface mode. Delegated takes priority over Internal.
    pub fn active_mode(&self) -> SurfaceMode {
        if self.has_delegated() {
            SurfaceMode::Delegated
        } else if self.surfaces.iter().any(|s| s.mode == SurfaceMode::Internal) {
            SurfaceMode::Internal
        } else {
            SurfaceMode::Headless
        }
    }

    /// Aggregate capabilities across all connected surfaces.
    /// A capability is available if ANY connected surface supports it.
    pub fn aggregate_capabilities(&self) -> SurfaceCapabilities {
        let mut caps = SurfaceCapabilities::default();
        for s in &self.surfaces {
            let c = &s.capabilities;
            caps.popup = caps.popup || c.popup;
            caps.menu = caps.menu || c.menu;
            caps.hud = caps.hud || c.hud;
            caps.notifications = caps.notifications || c.notifications;
            caps.rich_content = caps.rich_content || c.rich_content;
            caps.internal_tiling = caps.internal_tiling || c.internal_tiling;
            caps.external_tiling = caps.external_tiling || c.external_tiling;
            caps.detachable_panes = caps.detachable_panes || c.detachable_panes;
            caps.transparency = caps.transparency || c.transparency;
            caps.gaps = caps.gaps || c.gaps;
            caps.multi_window = caps.multi_window || c.multi_window;
            caps.keyboard = caps.keyboard || c.keyboard;
            caps.mouse = caps.mouse || c.mouse;
            caps.touch = caps.touch || c.touch;
            caps.persistent = caps.persistent || c.persistent;
            caps.multi_client = caps.multi_client || c.multi_client;
            caps.reconnectable = caps.reconnectable || c.reconnectable;
        }
        caps
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tauri_surface() -> SurfaceRegistration {
        SurfaceRegistration {
            id: "tauri-main".into(),
            name: "Tauri Desktop".into(),
            mode: SurfaceMode::Internal,
            capabilities: SurfaceCapabilities {
                popup: true,
                menu: true,
                hud: true,
                rich_content: true,
                internal_tiling: true,
                detachable_panes: true,
                transparency: true,
                gaps: true,
                multi_window: true,
                keyboard: true,
                mouse: true,
                ..Default::default()
            },
        }
    }

    fn tmux_surface() -> SurfaceRegistration {
        SurfaceRegistration {
            id: "tmux-0".into(),
            name: "tmux".into(),
            mode: SurfaceMode::Delegated,
            capabilities: SurfaceCapabilities {
                popup: true,
                menu: true,
                hud: true,
                notifications: true,
                external_tiling: true,
                keyboard: true,
                persistent: true,
                multi_client: true,
                reconnectable: true,
                ..Default::default()
            },
        }
    }

    fn cli_surface() -> SurfaceRegistration {
        SurfaceRegistration {
            id: "cli-1".into(),
            name: "CLI".into(),
            mode: SurfaceMode::Headless,
            capabilities: SurfaceCapabilities::default(),
        }
    }

    #[test]
    fn register_and_list() {
        let mut reg = SurfaceRegistry::new();
        reg.register(tauri_surface()).unwrap();
        assert_eq!(reg.list().len(), 1);
        assert_eq!(reg.list()[0].id, "tauri-main");
    }

    #[test]
    fn unregister() {
        let mut reg = SurfaceRegistry::new();
        reg.register(tauri_surface()).unwrap();
        assert!(reg.unregister("tauri-main"));
        assert_eq!(reg.list().len(), 0);
        assert!(!reg.unregister("nonexistent"));
    }

    #[test]
    fn reconnect_replaces() {
        let mut reg = SurfaceRegistry::new();
        reg.register(tauri_surface()).unwrap();
        reg.register(tauri_surface()).unwrap();
        assert_eq!(reg.list().len(), 1);
    }

    #[test]
    fn only_one_delegated() {
        let mut reg = SurfaceRegistry::new();
        reg.register(tmux_surface()).unwrap();
        let second = SurfaceRegistration {
            id: "sway-0".into(),
            name: "sway".into(),
            mode: SurfaceMode::Delegated,
            capabilities: SurfaceCapabilities::default(),
        };
        assert!(reg.register(second).is_err());
    }

    #[test]
    fn delegated_plus_internal_ok() {
        let mut reg = SurfaceRegistry::new();
        reg.register(tmux_surface()).unwrap();
        reg.register(tauri_surface()).unwrap();
        assert_eq!(reg.list().len(), 2);
    }

    #[test]
    fn active_mode_priority() {
        let mut reg = SurfaceRegistry::new();
        assert_eq!(reg.active_mode(), SurfaceMode::Headless);

        reg.register(cli_surface()).unwrap();
        assert_eq!(reg.active_mode(), SurfaceMode::Headless);

        reg.register(tauri_surface()).unwrap();
        assert_eq!(reg.active_mode(), SurfaceMode::Internal);

        reg.register(tmux_surface()).unwrap();
        assert_eq!(reg.active_mode(), SurfaceMode::Delegated);
    }

    #[test]
    fn aggregate_capabilities() {
        let mut reg = SurfaceRegistry::new();
        reg.register(cli_surface()).unwrap();
        let caps = reg.aggregate_capabilities();
        assert!(caps.keyboard);
        assert!(!caps.rich_content);

        reg.register(tauri_surface()).unwrap();
        let caps = reg.aggregate_capabilities();
        assert!(caps.rich_content);
        assert!(caps.internal_tiling);
        assert!(!caps.external_tiling);

        reg.register(tmux_surface()).unwrap();
        let caps = reg.aggregate_capabilities();
        assert!(caps.external_tiling);
        assert!(caps.internal_tiling);
    }

    #[test]
    fn serde_roundtrip() {
        let reg = tauri_surface();
        let json = serde_json::to_string(&reg).unwrap();
        let back: SurfaceRegistration = serde_json::from_str(&json).unwrap();
        assert_eq!(back.id, "tauri-main");
        assert_eq!(back.mode, SurfaceMode::Internal);
        assert!(back.capabilities.rich_content);
    }
}
