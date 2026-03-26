//! Persistence — serialize/deserialize workspace state and layout templates.
//!
//! Two concepts:
//! - WorkspaceSave: full runtime state (layout + panes + stacks)
//! - LayoutExport: reusable geometry template (layout tree only)

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::layout::{LayoutNode, LayoutTree};
use crate::stack_manager::StackManager;

/// Current schema version. Reject saves with a different version.
pub const CURRENT_VERSION: u32 = 1;

/// Full workspace snapshot for save/restore.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkspaceSave {
    pub version: u32,
    pub name: String,
    pub cwd: String,
    pub timestamp: String,
    pub layout: LayoutTree,
    pub panes: HashMap<String, PaneState>,
    pub stacks: StackManager,
}

/// Per-pane runtime metadata not captured by the layout tree.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaneState {
    pub cwd: Option<String>,
    pub command: Option<String>,
    #[serde(default)]
    pub args: Vec<String>,
}

/// Reusable layout geometry template (no runtime state).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayoutExport {
    pub name: String,
    pub description: Option<String>,
    pub root: LayoutNode,
}

/// Resolve the nexus home directory. Uses `NEXUS_HOME` env var if set,
/// otherwise defaults to `~/.nexus`.
pub fn nexus_home() -> PathBuf {
    std::env::var("NEXUS_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            dirs::home_dir()
                .unwrap_or_else(|| PathBuf::from("/tmp"))
                .join(".nexus")
        })
}

/// Session directory for a given workspace name.
pub fn session_dir(session_name: &str) -> PathBuf {
    nexus_home().join("sessions").join(session_name)
}

/// Global layouts directory.
pub fn global_layouts_dir() -> PathBuf {
    nexus_home().join("layouts")
}

/// Project-local layouts directory.
pub fn project_layouts_dir(cwd: &str) -> PathBuf {
    PathBuf::from(cwd).join(".nexus").join("layouts")
}

/// Save the auto-save checkpoint to `<session_dir>/state.json`.
pub fn save_workspace(session_dir: &Path, save: &WorkspaceSave) -> Result<(), String> {
    std::fs::create_dir_all(session_dir)
        .map_err(|e| format!("create session dir: {e}"))?;
    let json = serde_json::to_string_pretty(save)
        .map_err(|e| format!("serialize workspace: {e}"))?;
    let path = session_dir.join("state.json");
    std::fs::write(&path, json)
        .map_err(|e| format!("write {}: {e}", path.display()))
}

/// Load the auto-save checkpoint from `<session_dir>/state.json`.
pub fn load_workspace(session_dir: &Path) -> Result<WorkspaceSave, String> {
    let path = session_dir.join("state.json");
    let json = std::fs::read_to_string(&path)
        .map_err(|e| format!("read {}: {e}", path.display()))?;
    let save: WorkspaceSave = serde_json::from_str(&json)
        .map_err(|e| format!("parse {}: {e}", path.display()))?;
    if save.version != CURRENT_VERSION {
        return Err(format!(
            "unsupported version: {} (expected {})",
            save.version, CURRENT_VERSION
        ));
    }
    Ok(save)
}

/// Save a named snapshot to `<session_dir>/snapshots/<name>.json`.
pub fn save_snapshot(session_dir: &Path, name: &str, save: &WorkspaceSave) -> Result<String, String> {
    let snap_dir = session_dir.join("snapshots");
    std::fs::create_dir_all(&snap_dir)
        .map_err(|e| format!("create snapshots dir: {e}"))?;
    let path = snap_dir.join(format!("{name}.json"));
    let json = serde_json::to_string_pretty(save)
        .map_err(|e| format!("serialize snapshot: {e}"))?;
    std::fs::write(&path, &json)
        .map_err(|e| format!("write {}: {e}", path.display()))?;
    Ok(path.to_string_lossy().to_string())
}

/// Load a named snapshot from `<session_dir>/snapshots/<name>.json`.
pub fn load_snapshot(session_dir: &Path, name: &str) -> Result<WorkspaceSave, String> {
    let path = session_dir.join("snapshots").join(format!("{name}.json"));
    let json = std::fs::read_to_string(&path)
        .map_err(|e| format!("read {}: {e}", path.display()))?;
    let save: WorkspaceSave = serde_json::from_str(&json)
        .map_err(|e| format!("parse {}: {e}", path.display()))?;
    if save.version != CURRENT_VERSION {
        return Err(format!(
            "unsupported version: {} (expected {})",
            save.version, CURRENT_VERSION
        ));
    }
    Ok(save)
}

/// Delete a named snapshot.
pub fn delete_snapshot(session_dir: &Path, name: &str) -> Result<(), String> {
    let path = session_dir.join("snapshots").join(format!("{name}.json"));
    std::fs::remove_file(&path)
        .map_err(|e| format!("delete {}: {e}", path.display()))
}

/// List available snapshots. Returns list of snapshot info (name, timestamp, cwd).
pub fn list_snapshots(session_dir: &Path) -> Result<Vec<serde_json::Value>, String> {
    let snap_dir = session_dir.join("snapshots");
    if !snap_dir.exists() {
        return Ok(vec![]);
    }
    let mut results = Vec::new();
    let entries = std::fs::read_dir(&snap_dir)
        .map_err(|e| format!("read snapshots dir: {e}"))?;
    for entry in entries {
        let entry = entry.map_err(|e| format!("read entry: {e}"))?;
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) == Some("json") {
            if let Ok(json) = std::fs::read_to_string(&path) {
                if let Ok(save) = serde_json::from_str::<WorkspaceSave>(&json) {
                    let name = path
                        .file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("")
                        .to_string();
                    results.push(serde_json::json!({
                        "name": name,
                        "timestamp": save.timestamp,
                        "cwd": save.cwd,
                    }));
                }
            }
        }
    }
    Ok(results)
}

/// Save a layout export to `<layouts_dir>/<name>.json`.
pub fn save_layout_export(layouts_dir: &Path, export: &LayoutExport) -> Result<String, String> {
    std::fs::create_dir_all(layouts_dir)
        .map_err(|e| format!("create layouts dir: {e}"))?;
    let path = layouts_dir.join(format!("{}.json", export.name));
    let json = serde_json::to_string_pretty(export)
        .map_err(|e| format!("serialize layout: {e}"))?;
    std::fs::write(&path, &json)
        .map_err(|e| format!("write {}: {e}", path.display()))?;
    Ok(path.to_string_lossy().to_string())
}

/// Load a layout export from `<layouts_dir>/<name>.json`.
pub fn load_layout_export(layouts_dir: &Path, name: &str) -> Result<LayoutExport, String> {
    let path = layouts_dir.join(format!("{name}.json"));
    let json = std::fs::read_to_string(&path)
        .map_err(|e| format!("read {}: {e}", path.display()))?;
    serde_json::from_str(&json)
        .map_err(|e| format!("parse {}: {e}", path.display()))
}

/// List available layout exports. Returns list of layout names.
pub fn list_layout_exports(layouts_dir: &Path) -> Result<Vec<String>, String> {
    if !layouts_dir.exists() {
        return Ok(vec![]);
    }
    let mut names = Vec::new();
    let entries = std::fs::read_dir(layouts_dir)
        .map_err(|e| format!("read layouts dir: {e}"))?;
    for entry in entries {
        let entry = entry.map_err(|e| format!("read entry: {e}"))?;
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) == Some("json") {
            if let Some(name) = path.file_stem().and_then(|s| s.to_str()) {
                names.push(name.to_string());
            }
        }
    }
    Ok(names)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::layout::Direction;

    fn sample_layout() -> LayoutTree {
        LayoutTree::default_layout()
    }

    #[test]
    fn workspace_save_roundtrip() {
        let mut panes = HashMap::new();
        panes.insert("pane-1".to_string(), PaneState {
            cwd: Some("/tmp".to_string()),
            command: Some("/bin/zsh".to_string()),
            args: vec![],
        });

        let layout = sample_layout();
        let focused = layout.focused.clone();

        let save = WorkspaceSave {
            version: 1,
            name: "test-workspace".to_string(),
            cwd: "/tmp/project".to_string(),
            timestamp: "2026-03-25T10:00:00Z".to_string(),
            layout,
            panes,
            stacks: StackManager::new(),
        };

        let json = serde_json::to_string_pretty(&save).unwrap();
        let restored: WorkspaceSave = serde_json::from_str(&json).unwrap();

        assert_eq!(restored.version, 1);
        assert_eq!(restored.name, "test-workspace");
        assert_eq!(restored.layout.focused, focused);
        assert_eq!(restored.panes.len(), 1);
        assert_eq!(restored.panes["pane-1"].cwd, Some("/tmp".to_string()));
    }

    #[test]
    fn layout_export_roundtrip() {
        let export = LayoutExport {
            name: "dev-standard".to_string(),
            description: Some("4-pane dev layout".to_string()),
            root: LayoutNode::split(
                Direction::Horizontal,
                0.25,
                LayoutNode::leaf("p0"),
                LayoutNode::leaf("p1"),
            ),
        };

        let json = serde_json::to_string_pretty(&export).unwrap();
        let restored: LayoutExport = serde_json::from_str(&json).unwrap();

        assert_eq!(restored.name, "dev-standard");
        assert_eq!(restored.description, Some("4-pane dev layout".to_string()));
        assert_eq!(restored.root.leaf_ids().len(), 2);
    }

    #[test]
    fn pane_state_defaults_empty_args() {
        let json = r#"{"cwd":null,"command":null}"#;
        let state: PaneState = serde_json::from_str(json).unwrap();
        assert!(state.args.is_empty());
    }
}
