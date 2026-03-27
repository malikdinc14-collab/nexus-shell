//! Menu Engine — cascading discovery, script providers, live data.
//!
//! Discovery layers (later overrides earlier):
//!   1. Global:    $NEXUS_HOME/menu/
//!   2. User:      ~/.nexus/menu/
//!   3. Profile:   ~/.nexus/profiles/<active>/menu/
//!   4. Project:   $PROJECT_ROOT/.nexus/menu/
//!
//! Each layer directory contains YAML files (submenus) and optional
//! executable scripts (live data providers).

use nexus_core::NexusError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::process::Command;

// ── Data model ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MenuItem {
    pub label: String,
    #[serde(rename = "type")]
    pub item_type: String,
    #[serde(default)]
    pub payload: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub icon: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    /// Extra key-value metadata (keybinding hints, source path, etc.)
    #[serde(flatten)]
    pub meta: HashMap<String, serde_json::Value>,
}

impl MenuItem {
    pub fn new(label: &str, item_type: &str, description: &str) -> Self {
        Self {
            label: label.to_string(),
            item_type: item_type.to_string(),
            payload: String::new(),
            icon: None,
            description: Some(description.to_string()),
            meta: HashMap::new(),
        }
    }

    pub fn with_arg(mut self, key: &str, value: &str) -> Self {
        self.meta.insert(key.to_string(), serde_json::Value::String(value.to_string()));
        self
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MenuList {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub icon: Option<String>,
    #[serde(default)]
    pub layout: String, // "list" | "grid"
    #[serde(default)]
    pub items: Vec<MenuItem>,
}

impl Default for MenuList {
    fn default() -> Self {
        Self {
            name: String::new(),
            icon: None,
            layout: "list".into(),
            items: Vec::new(),
        }
    }
}

// ── Menu Engine ─────────────────────────────────────────────────────────

pub struct MenuEngine {
    /// Discovery layer roots, ordered lowest → highest priority.
    layers: Vec<PathBuf>,
    /// Navigation history (context strings).
    history: Vec<String>,
    /// Current context.
    current: String,
}

impl MenuEngine {
    /// Create a new MenuEngine with discovery layers resolved from the environment.
    pub fn new(nexus_home: Option<&Path>, project_root: Option<&Path>, profile: Option<&str>) -> Self {
        let mut layers = Vec::new();

        // 1. Global (nexus_home/menu/)
        if let Some(home) = nexus_home {
            layers.push(home.join("menu"));
        }

        // 2. User (~/.nexus/menu/)
        if let Some(home_dir) = dirs::home_dir() {
            layers.push(home_dir.join(".nexus").join("menu"));
        }

        // 3. Profile (~/.nexus/profiles/<profile>/menu/)
        if let (Some(prof), Some(home_dir)) = (profile, dirs::home_dir()) {
            if !prof.is_empty() {
                layers.push(
                    home_dir
                        .join(".nexus")
                        .join("profiles")
                        .join(prof)
                        .join("menu"),
                );
            }
        }

        // 4. Project ($PROJECT_ROOT/.nexus/menu/)
        if let Some(root) = project_root {
            layers.push(root.join(".nexus").join("menu"));
        }

        Self {
            layers,
            history: Vec::new(),
            current: "home".into(),
        }
    }

    /// Get menu items for a context. Cascading: later layers override earlier.
    pub fn get(&mut self, context: &str) -> MenuList {
        self.current = context.to_string();

        // Special built-in contexts
        match context {
            "home" => return self.resolve_home(),
            "modules" => return self.builtin_modules(),
            "settings" => return self.builtin_settings(),
            _ => {}
        }

        // Resolve from layers
        self.resolve_context(context)
    }

    /// Navigate into a folder context, pushing current to history.
    pub fn navigate(&mut self, context: &str) -> MenuList {
        self.history.push(self.current.clone());
        self.get(context)
    }

    /// Go back in history. Returns parent context items.
    pub fn back(&mut self) -> MenuList {
        let prev = self.history.pop().unwrap_or_else(|| "home".into());
        self.get(&prev)
    }

    /// Current context name.
    pub fn current_context(&self) -> &str {
        &self.current
    }

    /// History depth (for UI back-button visibility).
    pub fn history_depth(&self) -> usize {
        self.history.len()
    }

    // ── Resolution ──────────────────────────────────────────────────────

    fn resolve_home(&self) -> MenuList {
        // Try to find home.yaml across layers (highest priority wins)
        for layer in self.layers.iter().rev() {
            let home_file = layer.join("home.yaml");
            if home_file.exists() {
                if let Ok(list) = load_yaml_menu(&home_file) {
                    return list;
                }
            }
        }

        // Fallback: built-in home
        self.builtin_home()
    }

    fn resolve_context(&self, context: &str) -> MenuList {
        // Context maps to a subdirectory or yaml file in each layer.
        // e.g. context "tools" looks for: <layer>/tools.yaml or <layer>/tools/
        let mut merged = MenuList {
            name: context.to_string(),
            ..Default::default()
        };
        let mut seen_labels: std::collections::HashSet<String> = std::collections::HashSet::new();

        for layer in &self.layers {
            // Try YAML file first
            let yaml_path = layer.join(format!("{context}.yaml"));
            if yaml_path.exists() {
                if let Ok(list) = load_yaml_menu(&yaml_path) {
                    if merged.name == context {
                        merged.name = list.name;
                    }
                    if list.icon.is_some() {
                        merged.icon = list.icon;
                    }
                    if !list.layout.is_empty() {
                        merged.layout = list.layout;
                    }
                    for item in list.items {
                        if seen_labels.insert(item.label.clone()) {
                            merged.items.push(item);
                        }
                    }
                }
            }

            // Then scan directory
            let dir_path = layer.join(context);
            if dir_path.is_dir() {
                self.scan_directory(&dir_path, &mut merged.items, &mut seen_labels);
            }
        }

        merged
    }

    fn scan_directory(
        &self,
        dir: &Path,
        items: &mut Vec<MenuItem>,
        seen: &mut std::collections::HashSet<String>,
    ) {
        let mut entries: Vec<_> = match std::fs::read_dir(dir) {
            Ok(rd) => rd.filter_map(|e| e.ok()).collect(),
            Err(_) => return,
        };
        entries.sort_by_key(|e| e.file_name());

        for entry in entries {
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with('_') || name.starts_with('.') {
                continue;
            }

            let path = entry.path();

            if path.is_dir() {
                // Subdirectory → folder item
                let label = name.clone();
                if seen.insert(label.clone()) {
                    items.push(MenuItem {
                        label,
                        item_type: "folder".into(),
                        payload: format!("{}/{name}", dir.file_name().unwrap_or_default().to_string_lossy()),
                        icon: None,
                        description: None,
                        meta: HashMap::new(),
                    });
                }
            } else if is_executable(&path) {
                // Executable script → run for live data
                if let Ok(live_items) = run_script_provider(&path) {
                    for item in live_items {
                        if seen.insert(item.label.clone()) {
                            items.push(item);
                        }
                    }
                }
            } else if name.ends_with(".yaml") || name.ends_with(".yml") {
                // YAML file → submenu folder pointer
                let stem = path.file_stem().unwrap_or_default().to_string_lossy().to_string();
                if seen.insert(stem.clone()) {
                    let desc = load_yaml_menu(&path)
                        .ok()
                        .and_then(|m| if m.name.is_empty() { None } else { Some(m.name) });
                    items.push(MenuItem {
                        label: stem.clone(),
                        item_type: "folder".into(),
                        payload: format!(
                            "{}/{}",
                            dir.file_name().unwrap_or_default().to_string_lossy(),
                            stem
                        ),
                        icon: None,
                        description: desc,
                        meta: HashMap::new(),
                    });
                }
            } else {
                // Other files → action items
                let stem = path.file_stem().unwrap_or_default().to_string_lossy().to_string();
                if seen.insert(stem.clone()) {
                    items.push(MenuItem {
                        label: stem,
                        item_type: "file".into(),
                        payload: path.to_string_lossy().to_string(),
                        icon: None,
                        description: None,
                        meta: HashMap::new(),
                    });
                }
            }
        }
    }

    // ── Built-in menus ──────────────────────────────────────────────────

    fn builtin_home(&self) -> MenuList {
        MenuList {
            name: "Nexus Hub".into(),
            icon: Some("H".into()),
            layout: "list".into(),
            items: vec![
                MenuItem {
                    label: "Modules".into(),
                    item_type: "folder".into(),
                    payload: "modules".into(),
                    icon: Some("M".into()),
                    description: Some("Open a module in this pane".into()),
                    meta: HashMap::new(),
                },
                MenuItem {
                    label: "Settings".into(),
                    item_type: "folder".into(),
                    payload: "settings".into(),
                    icon: Some("S".into()),
                    description: Some("View and edit configuration".into()),
                    meta: HashMap::new(),
                },
                MenuItem {
                    label: "separator".into(),
                    item_type: "separator".into(),
                    payload: String::new(),
                    icon: None,
                    description: None,
                    meta: HashMap::new(),
                },
            ],
        }
    }

    fn builtin_modules(&self) -> MenuList {
        MenuList {
            name: "Modules".into(),
            icon: Some("M".into()),
            layout: "grid".into(),
            items: vec![
                module_item("Terminal", "T", "Terminal emulator"),
                module_item("Editor", "E", "Code editor"),
                module_item("Explorer", "F", "File browser"),
                module_item("Chat", "C", "AI assistant"),
                module_item("Browser", "W", "Web browser"),
                module_item("RichText", "R", "Rich text editor"),
                module_item("HUD", "H", "System HUD"),
                module_item("Settings", "S", "Appearance settings"),
                module_item("Menu", "=", "Menu browser"),
                module_item("Info", "i", "System info"),
            ],
        }
    }

    fn builtin_settings(&self) -> MenuList {
        let mut items = Vec::new();

        // Scan for config files across layers
        for layer in &self.layers {
            let parent = layer.parent().unwrap_or(layer);
            // Look for common config files
            for name in &["config.yaml", "profile.yaml", "keymap.conf", "theme.yaml"] {
                let path = parent.join(name);
                if path.exists() {
                    items.push(MenuItem {
                        label: name.to_string(),
                        item_type: "settings".into(),
                        payload: path.to_string_lossy().to_string(),
                        icon: Some("S".into()),
                        description: Some(format!("Edit {name}")),
                        meta: HashMap::new(),
                    });
                }
            }
        }

        if items.is_empty() {
            items.push(MenuItem {
                label: "No config files found".into(),
                item_type: "info".into(),
                payload: String::new(),
                icon: Some("i".into()),
                description: Some("Create ~/.nexus/config.yaml to get started".into()),
                meta: HashMap::new(),
            });
        }

        MenuList {
            name: "Settings".into(),
            icon: Some("S".into()),
            layout: "list".into(),
            items,
        }
    }
}

// ── Helpers ─────────────────────────────────────────────────────────────

fn module_item(name: &str, icon: &str, desc: &str) -> MenuItem {
    MenuItem {
        label: name.into(),
        item_type: "module".into(),
        payload: name.into(),
        icon: Some(icon.into()),
        description: Some(desc.into()),
        meta: HashMap::new(),
    }
}

fn load_yaml_menu(path: &Path) -> Result<MenuList, NexusError> {
    let content = std::fs::read_to_string(path).map_err(|e| NexusError::Io(e.to_string()))?;
    serde_yaml::from_str(&content).map_err(|e| NexusError::Protocol(e.to_string()))
}

fn is_executable(path: &Path) -> bool {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = std::fs::metadata(path) {
            return meta.permissions().mode() & 0o111 != 0;
        }
    }
    false
}

fn run_script_provider(path: &Path) -> Result<Vec<MenuItem>, NexusError> {
    let output = Command::new(path)
        .env("NEXUS_MENU", "1")
        .output()
        .map_err(|e| NexusError::Io(e.to_string()))?;

    if !output.status.success() {
        return Err(NexusError::Io(format!("script exited with {}", output.status)));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut items = Vec::new();

    for line in stdout.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }

        // Try JSON first
        if line.starts_with('{') {
            if let Ok(item) = serde_json::from_str::<MenuItem>(line) {
                items.push(item);
                continue;
            }
        }

        // Fallback: TSV (label\ttype\tpayload)
        let parts: Vec<&str> = line.splitn(3, '\t').collect();
        if parts.len() >= 3 {
            items.push(MenuItem {
                label: parts[0].into(),
                item_type: parts[1].into(),
                payload: parts[2].into(),
                icon: None,
                description: None,
                meta: HashMap::new(),
            });
        } else {
            // Plain text → action item
            items.push(MenuItem {
                label: line.into(),
                item_type: "action".into(),
                payload: line.into(),
                icon: None,
                description: None,
                meta: HashMap::new(),
            });
        }
    }

    Ok(items)
}

// ── Tests ───────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn builtin_home_has_modules_and_settings() {
        let engine = MenuEngine::new(None, None, None);
        let mut engine = engine;
        let home = engine.get("home");
        assert_eq!(home.name, "Nexus Hub");
        assert!(home.items.iter().any(|i| i.label == "Modules"));
        assert!(home.items.iter().any(|i| i.label == "Settings"));
    }

    #[test]
    fn builtin_modules_has_core_items() {
        let mut engine = MenuEngine::new(None, None, None);
        let mods = engine.get("modules");
        assert_eq!(mods.name, "Modules");
        let labels: Vec<&str> = mods.items.iter().map(|i| i.label.as_str()).collect();
        assert!(labels.contains(&"Terminal"));
        assert!(labels.contains(&"Editor"));
        assert!(labels.contains(&"Chat"));
    }

    #[test]
    fn navigation_history() {
        let mut engine = MenuEngine::new(None, None, None);
        engine.get("home");
        let _ = engine.navigate("modules");
        assert_eq!(engine.history_depth(), 1);
        assert_eq!(engine.current_context(), "modules");
        let back = engine.back();
        assert_eq!(back.name, "Nexus Hub");
        assert_eq!(engine.history_depth(), 0);
    }

    #[test]
    fn yaml_menu_discovery() {
        let tmp = tempfile::tempdir().unwrap();
        let menu_dir = tmp.path().join("menu");
        fs::create_dir_all(&menu_dir).unwrap();
        fs::write(
            menu_dir.join("tools.yaml"),
            r#"
name: Developer Tools
layout: list
items:
  - label: Git Status
    type: action
    payload: "git status"
    description: Show git status
  - label: Docker
    type: folder
    payload: tools/docker
"#,
        )
        .unwrap();

        let mut engine = MenuEngine::new(Some(tmp.path()), None, None);
        let tools = engine.get("tools");
        assert_eq!(tools.name, "Developer Tools");
        assert_eq!(tools.items.len(), 2);
        assert_eq!(tools.items[0].label, "Git Status");
        assert_eq!(tools.items[1].item_type, "folder");
    }

    #[test]
    fn cascading_layers_higher_priority_wins() {
        let global = tempfile::tempdir().unwrap();
        let project = tempfile::tempdir().unwrap();

        let g_menu = global.path().join("menu");
        let p_menu = project.path().join(".nexus").join("menu");
        fs::create_dir_all(&g_menu).unwrap();
        fs::create_dir_all(&p_menu).unwrap();

        // Global has home.yaml with name "Global Hub"
        fs::write(
            g_menu.join("home.yaml"),
            "name: Global Hub\nitems:\n  - label: Global Item\n    type: action\n    payload: global\n",
        )
        .unwrap();

        // Project has home.yaml with name "Project Hub" (should win)
        fs::write(
            p_menu.join("home.yaml"),
            "name: Project Hub\nitems:\n  - label: Project Item\n    type: action\n    payload: project\n",
        )
        .unwrap();

        let mut engine = MenuEngine::new(Some(global.path()), Some(project.path()), None);
        let home = engine.get("home");
        // Project layer is highest priority, so it wins
        assert_eq!(home.name, "Project Hub");
    }

    #[test]
    fn script_provider_parses_json() {
        let tmp = tempfile::tempdir().unwrap();
        let menu_dir = tmp.path().join("menu").join("live");
        fs::create_dir_all(&menu_dir).unwrap();

        let script = menu_dir.join("ports.sh");
        fs::write(
            &script,
            r#"#!/bin/sh
echo '{"label":"Port 8080","type":"live","payload":"8080","description":"HTTP server"}'
echo '{"label":"Port 3000","type":"live","payload":"3000","description":"Dev server"}'
"#,
        )
        .unwrap();

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(&script, fs::Permissions::from_mode(0o755)).unwrap();
        }

        let mut engine = MenuEngine::new(Some(tmp.path()), None, None);
        let live = engine.get("live");
        assert_eq!(live.items.len(), 2);
        assert_eq!(live.items[0].label, "Port 8080");
        assert_eq!(live.items[1].payload, "3000");
    }
}
