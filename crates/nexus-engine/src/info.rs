//! Info Engine — system information provider.
//!
//! Produces structured data about the current Nexus state:
//! session, cwd, layout, panes, display, stacks, capabilities.
//! Any surface (Tauri, TUI, CLI) calls `info.get` and renders the result.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::core::NexusCore;

// ── Data model ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InfoData {
    pub session: Option<String>,
    pub cwd: String,
    pub layout: LayoutInfo,
    pub display: DisplayInfo,
    pub backends: BackendsInfo,
    pub stacks: Vec<StackInfo>,
    pub surfaces: Vec<SurfaceInfo>,
    pub system: SystemInfo,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendEntry {
    pub module: String,
    pub backend: String,
    pub available: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendsInfo {
    pub entries: Vec<BackendEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayoutInfo {
    pub pane_count: usize,
    pub focused: String,
    pub zoomed: Option<String>,
    pub panes: Vec<PaneInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaneInfo {
    pub id: String,
    pub is_focused: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DisplayInfo {
    pub gap: u32,
    pub background: String,
    pub border_radius: u32,
    pub pane_opacity: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StackInfo {
    pub identity: String,
    pub tab_count: usize,
    pub active_tab: String,
    pub tabs: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceInfo {
    pub id: String,
    pub name: String,
    pub mode: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemInfo {
    pub version: String,
    pub pid: u32,
    pub uptime_secs: u64,
}

// ── Info Engine ─────────────────────────────────────────────────────────

/// Collects system info from NexusCore. Stateless — just reads core state.
pub fn collect(core: &NexusCore) -> InfoData {
    let pane_ids = core.layout.root.leaf_ids();

    let panes: Vec<PaneInfo> = pane_ids
        .iter()
        .map(|id| PaneInfo {
            id: id.clone(),
            is_focused: *id == core.layout.focused,
        })
        .collect();

    let layout = LayoutInfo {
        pane_count: panes.len(),
        focused: core.layout.focused.clone(),
        zoomed: core.layout.zoomed.clone(),
        panes,
    };

    let display = DisplayInfo {
        gap: core.display.gap,
        background: core.display.background.clone(),
        border_radius: core.display.border_radius,
        pane_opacity: core.display.pane_opacity,
    };

    // Collect stack info
    let stacks: Vec<StackInfo> = pane_ids
        .iter()
        .filter_map(|pane_id| {
            let (_sid, stack) = core.stacks.get_by_identity(pane_id)?;
            let active_tab = stack
                .tabs
                .get(stack.active_index)
                .map(|t| t.name.clone())
                .unwrap_or_default();
            let tabs: Vec<String> = stack.tabs.iter().map(|t| t.name.clone()).collect();
            Some(StackInfo {
                identity: pane_id.clone(),
                tab_count: tabs.len(),
                active_tab,
                tabs,
            })
        })
        .collect();

    // Collect surface info
    let surfaces: Vec<SurfaceInfo> = core
        .surfaces
        .list()
        .iter()
        .map(|reg| SurfaceInfo {
            id: reg.id.clone(),
            name: reg.name.clone(),
            mode: format!("{:?}", reg.mode),
        })
        .collect();

    // Collect backend info
    let backends = BackendsInfo {
        entries: vec![
            BackendEntry {
                module: "explorer".into(),
                backend: core.explorer.backend_name().to_string(),
                available: true,
            },
            BackendEntry {
                module: "editor".into(),
                backend: core.editor.backend_name().to_string(),
                available: true,
            },
            BackendEntry {
                module: "chat".into(),
                backend: core.chat.backend_name().to_string(),
                available: true,
            },
            BackendEntry {
                module: "terminal".into(),
                backend: core.terminal.backend_name().to_string(),
                available: true,
            },
        ],
    };

    let system = SystemInfo {
        version: env!("CARGO_PKG_VERSION").to_string(),
        pid: std::process::id(),
        uptime_secs: 0, // TODO: track start time
    };

    InfoData {
        session: core.session().map(|s| s.to_string()),
        cwd: core.cwd().to_string(),
        layout,
        display,
        backends,
        stacks,
        surfaces,
        system,
    }
}

/// Collect a specific section of info.
pub fn collect_section(core: &NexusCore, section: &str) -> serde_json::Value {
    let full = collect(core);
    match section {
        "layout" => serde_json::to_value(&full.layout).unwrap_or_default(),
        "display" => serde_json::to_value(&full.display).unwrap_or_default(),
        "stacks" => serde_json::to_value(&full.stacks).unwrap_or_default(),
        "surfaces" => serde_json::to_value(&full.surfaces).unwrap_or_default(),
        "system" => serde_json::to_value(&full.system).unwrap_or_default(),
        _ => serde_json::to_value(&full).unwrap_or_default(),
    }
}

// ── Tests ───────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::surface::NullMux;

    #[test]
    fn collect_returns_valid_info() {
        let core = NexusCore::new(Box::new(NullMux::new()));
        let info = collect(&core);
        assert!(info.layout.pane_count > 0);
        assert!(!info.layout.focused.is_empty());
        assert!(!info.system.version.is_empty());
    }

    #[test]
    fn collect_section_layout() {
        let core = NexusCore::new(Box::new(NullMux::new()));
        let section = collect_section(&core, "layout");
        assert!(section.get("pane_count").is_some());
        assert!(section.get("focused").is_some());
    }

    #[test]
    fn collect_section_unknown_returns_full() {
        let core = NexusCore::new(Box::new(NullMux::new()));
        let section = collect_section(&core, "everything");
        assert!(section.get("session").is_some());
        assert!(section.get("layout").is_some());
        assert!(section.get("system").is_some());
    }
}
