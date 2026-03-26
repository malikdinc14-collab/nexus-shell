//! TmuxMux — Mux implementation that dispatches to tmux via CLI.
//!
//! All tmux operations use `std::process::Command` to call the `tmux` binary.
//! An optional socket label enables per-project tmux server isolation.

use nexus_core::mux::{
    ContainerInfo, Dimensions, Geometry, HudModule, MenuItem, Mux, SplitDirection,
};
use std::collections::HashMap;
use std::process::Command;

/// Nexus Mux adapter for tmux.
pub struct TmuxMux {
    /// Optional tmux socket label (e.g. "nexus_myproject").
    /// If set, passed as `-L <label>` to all tmux commands.
    /// If starts with `/`, passed as `-S <path>` instead.
    socket_label: Option<String>,
    /// In-process tag store. tmux pane options (`@key`) are the canonical
    /// store, but we cache here to avoid shelling out on every get_tag.
    tags: HashMap<(String, String), String>,
}

impl TmuxMux {
    pub fn new() -> Self {
        Self {
            socket_label: None,
            tags: HashMap::new(),
        }
    }

    pub fn with_socket(label: &str) -> Self {
        Self {
            socket_label: Some(label.to_string()),
            tags: HashMap::new(),
        }
    }

    /// Execute a tmux command and return stdout, or None on failure.
    fn tmux(&self, args: &[&str]) -> Option<String> {
        let mut cmd = Command::new("tmux");
        if let Some(ref label) = self.socket_label {
            if label.starts_with('/') {
                cmd.args(["-S", label]);
            } else {
                cmd.args(["-L", label]);
            }
        }
        cmd.args(args);

        match cmd.output() {
            Ok(output) if output.status.success() => {
                let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if stdout.is_empty() { Some(String::new()) } else { Some(stdout) }
            }
            Ok(output) => {
                let stderr = String::from_utf8_lossy(&output.stderr);
                eprintln!("[tmux] command failed: tmux {} — {}", args.join(" "), stderr.trim());
                None
            }
            Err(e) => {
                eprintln!("[tmux] failed to execute: {e}");
                None
            }
        }
    }
}

impl Default for TmuxMux {
    fn default() -> Self {
        Self::new()
    }
}

impl Mux for TmuxMux {
    // ── Lifecycle ────────────────────────────────────────────────────────

    fn initialize(&mut self, session_name: &str, cwd: &str) -> String {
        let mut args = vec![
            "new-session", "-d", "-s", session_name, "-P", "-F", "#{session_id}",
        ];
        if !cwd.is_empty() {
            args.extend(["-c", cwd]);
        }
        self.tmux(&args).unwrap_or_else(|| session_name.to_string())
    }

    fn teardown(&mut self, session: &str) {
        self.tmux(&["kill-session", "-t", session]);
    }

    // ── Spatial ──────────────────────────────────────────────────────────

    fn create_container(&mut self, session: &str, command: &str, cwd: &str) -> String {
        let mut args = vec![
            "new-window", "-t", session, "-P", "-F", "#{pane_id}",
        ];
        if !cwd.is_empty() {
            args.extend(["-c", cwd]);
        }
        if !command.is_empty() {
            args.push(command);
        }
        self.tmux(&args).unwrap_or_default()
    }

    fn split(
        &mut self,
        handle: &str,
        direction: SplitDirection,
        size: Option<u32>,
        cwd: &str,
    ) -> String {
        let flag = match direction {
            SplitDirection::Horizontal => "-h",
            SplitDirection::Vertical => "-v",
        };
        let mut args = vec![
            "split-window", flag, "-t", handle, "-P", "-F", "#{pane_id}",
        ];
        let size_str;
        if let Some(s) = size {
            size_str = s.to_string();
            args.extend(["-l", &size_str]);
        }
        if !cwd.is_empty() {
            args.extend(["-c", cwd]);
        }
        self.tmux(&args).unwrap_or_default()
    }

    fn destroy_container(&mut self, handle: &str) {
        self.tmux(&["kill-pane", "-t", handle]);
    }

    fn focus(&mut self, handle: &str) {
        self.tmux(&["select-pane", "-t", handle]);
    }

    fn resize(&mut self, handle: &str, dimensions: Dimensions) {
        let w = dimensions.width.to_string();
        let h = dimensions.height.to_string();
        self.tmux(&["resize-pane", "-t", handle, "-x", &w, "-y", &h]);
    }

    // ── Swap ─────────────────────────────────────────────────────────────

    fn swap_containers(&mut self, source: &str, target: &str) -> bool {
        if source == target {
            return true;
        }
        // Verify both panes exist before swapping
        let all_panes = self.tmux(&["list-panes", "-a", "-F", "#{pane_id}"]);
        let pane_list: Vec<&str> = all_panes
            .as_deref()
            .map(|s| s.lines().collect())
            .unwrap_or_default();

        if !pane_list.contains(&source) || !pane_list.contains(&target) {
            return false;
        }

        self.tmux(&["swap-pane", "-d", "-s", source, "-t", target])
            .is_some()
    }

    fn container_exists(&self, handle: &str) -> bool {
        if handle.is_empty() {
            return false;
        }
        let all_panes = self.tmux(&["list-panes", "-a", "-F", "#{pane_id}"]);
        all_panes
            .as_deref()
            .map(|s| s.lines().any(|line| line == handle))
            .unwrap_or(false)
    }

    // ── Content ──────────────────────────────────────────────────────────

    fn attach_process(&mut self, handle: &str, command: &str) {
        self.tmux(&["send-keys", "-t", handle, command, "Enter"]);
    }

    fn send_input(&mut self, handle: &str, keys: &str) {
        self.tmux(&["send-keys", "-t", handle, keys]);
    }

    // ── State ────────────────────────────────────────────────────────────

    fn list_containers(&self, session: &str) -> Vec<ContainerInfo> {
        let fmt = "#{pane_id}\t#{pane_index}\t#{pane_width}\t#{pane_height}\t#{pane_left}\t#{pane_top}\t#{pane_current_command}\t#{pane_title}\t#{pane_active}";
        let result = self.tmux(&["list-panes", "-t", session, "-F", fmt]);
        let Some(output) = result else { return Vec::new() };

        output
            .lines()
            .filter_map(|line| {
                let parts: Vec<&str> = line.split('\t').collect();
                if parts.len() < 9 {
                    return None;
                }
                Some(ContainerInfo {
                    handle: parts[0].to_string(),
                    index: parts[1].parse().unwrap_or(0),
                    width: parts[2].parse().unwrap_or(80),
                    height: parts[3].parse().unwrap_or(24),
                    x: parts[4].parse().unwrap_or(0),
                    y: parts[5].parse().unwrap_or(0),
                    command: parts[6].to_string(),
                    title: parts[7].to_string(),
                    focused: parts[8] == "1",
                    tags: HashMap::new(),
                })
            })
            .collect()
    }

    fn get_focused(&self, session: &str) -> Option<String> {
        self.tmux(&["display-message", "-t", session, "-p", "#{pane_id}"])
            .filter(|s| !s.is_empty())
    }

    fn get_dimensions(&self, handle: &str) -> Dimensions {
        let result = self.tmux(&[
            "display-message", "-t", handle, "-p", "#{pane_width},#{pane_height}",
        ]);
        if let Some(s) = result {
            if let Some((w, h)) = s.split_once(',') {
                return Dimensions {
                    width: w.parse().unwrap_or(80),
                    height: h.parse().unwrap_or(24),
                };
            }
        }
        Dimensions { width: 80, height: 24 }
    }

    fn get_geometry(&self, handle: &str) -> Option<Geometry> {
        let result = self.tmux(&[
            "display-message", "-t", handle, "-p",
            "#{pane_left},#{pane_top},#{pane_width},#{pane_height}",
        ])?;
        let parts: Vec<&str> = result.split(',').collect();
        if parts.len() < 4 {
            return None;
        }
        Some(Geometry {
            x: parts[0].parse().unwrap_or(0),
            y: parts[1].parse().unwrap_or(0),
            w: parts[2].parse().unwrap_or(80),
            h: parts[3].parse().unwrap_or(24),
        })
    }

    fn set_geometry(&mut self, handle: &str, geometry: &Geometry) {
        let w = geometry.w.to_string();
        let h = geometry.h.to_string();
        self.tmux(&["resize-pane", "-t", handle, "-x", &w, "-y", &h]);
    }

    // ── Metadata ─────────────────────────────────────────────────────────

    fn set_tag(&mut self, handle: &str, key: &str, value: &str) {
        let opt_key = format!("@{key}");
        self.tmux(&["set-option", "-p", "-t", handle, &opt_key, value]);
        self.tags
            .insert((handle.to_string(), key.to_string()), value.to_string());
    }

    fn get_tag(&self, handle: &str, key: &str) -> String {
        // Try cache first
        if let Some(v) = self.tags.get(&(handle.to_string(), key.to_string())) {
            return v.clone();
        }
        // Fall back to tmux query
        let fmt = format!("#{{@{key}}}");
        self.tmux(&["display-message", "-p", "-t", handle, &fmt])
            .unwrap_or_default()
    }

    fn set_title(&mut self, handle: &str, title: &str) {
        self.tmux(&["select-pane", "-t", handle, "-T", title]);
    }

    // ── Layout ───────────────────────────────────────────────────────────

    fn apply_layout(&mut self, _session: &str, _layout: &serde_json::Value) -> bool {
        // Layout application is handled by the engine's LayoutTree.
        // Future: convert LayoutTree to tmux layout string and apply.
        false
    }

    fn capture_layout(&self, session: &str) -> serde_json::Value {
        let containers = self.list_containers(session);
        serde_json::json!({
            "containers": containers.iter().map(|c| serde_json::json!({
                "handle": c.handle,
                "width": c.width,
                "height": c.height,
                "x": c.x,
                "y": c.y,
                "command": c.command,
            })).collect::<Vec<_>>()
        })
    }

    // ── Environment ──────────────────────────────────────────────────────

    fn set_env(&mut self, session: &str, key: &str, value: &str) {
        self.tmux(&["set-environment", "-t", session, key, value]);
    }

    // ── Optional rendering ───────────────────────────────────────────────

    fn show_popup(&mut self, command: &str, width: u32, height: u32) -> bool {
        let w = format!("{width}");
        let h = format!("{height}");
        self.tmux(&["display-popup", "-w", &w, "-h", &h, "-E", command])
            .is_some()
    }

    fn show_menu(&mut self, items: &[MenuItem], _prompt: &str) -> Option<String> {
        // Build tmux display-menu arguments
        // Format: display-menu "label1" "key1" "action1" "label2" "key2" "action2" ...
        if items.is_empty() {
            return None;
        }
        let mut args: Vec<String> = vec!["display-menu".into()];
        for (i, item) in items.iter().enumerate() {
            args.push(item.label.clone());
            // Use first char as shortcut key, or index
            let key = item.label.chars().next()
                .map(|c| c.to_string())
                .unwrap_or_else(|| i.to_string());
            args.push(key);
            // Action: run nexus dispatch with the item id
            args.push(format!("run-shell 'nexus dispatch {}'", item.id));
        }
        let arg_refs: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        self.tmux(&arg_refs);
        // tmux display-menu is interactive — selection happens asynchronously
        None
    }

    fn show_hud(&mut self, modules: &[HudModule]) {
        // Build status-right from HUD modules
        let mut left_parts = Vec::new();
        let mut right_parts = Vec::new();

        for m in modules {
            let part = if let Some(ref color) = m.color {
                format!("#[fg={color}]{}: {}#[default]", m.label, m.value)
            } else {
                format!("{}: {}", m.label, m.value)
            };
            match m.position.as_str() {
                "left" => left_parts.push(part),
                _ => right_parts.push(part),
            }
        }

        if !left_parts.is_empty() {
            let left = left_parts.join(" | ");
            self.tmux(&["set-option", "-g", "status-left", &left]);
        }
        if !right_parts.is_empty() {
            let right = right_parts.join(" | ");
            self.tmux(&["set-option", "-g", "status-right", &right]);
        }
    }

    fn notify(&mut self, message: &str, _level: &str) -> bool {
        self.tmux(&["display-message", message]).is_some()
    }

    fn supports_popup(&self) -> bool { true }
    fn supports_menu(&self) -> bool { true }
    fn supports_notify(&self) -> bool { true }
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
    fn tmux_mux_tags_cache() {
        let mut mux = TmuxMux::new();
        // Tags are cached in-process even without tmux running
        mux.tags.insert(("pane1".into(), "role".into()), "editor".into());
        assert_eq!(mux.get_tag("pane1", "role"), "editor");
        assert_eq!(mux.get_tag("pane1", "missing"), "");
    }

    #[test]
    fn tmux_mux_socket_label() {
        let mux = TmuxMux::with_socket("nexus_test");
        assert_eq!(mux.socket_label.as_deref(), Some("nexus_test"));
    }

    #[test]
    fn tmux_mux_supports_optional_features() {
        let mux = TmuxMux::new();
        assert!(mux.supports_popup());
        assert!(mux.supports_menu());
        assert!(mux.supports_notify());
    }

    // Integration tests that require a real tmux server
    // Run with: NEXUS_TEST_TMUX=1 cargo test -p nexus-tmux -- --ignored
    #[test]
    #[ignore = "requires tmux to be installed and available"]
    fn integration_session_lifecycle() {
        let mut mux = TmuxMux::with_socket("nexus_test_integration");
        let session = mux.initialize("nexus-test", "/tmp");
        assert!(!session.is_empty());

        let containers = mux.list_containers("nexus-test");
        assert!(!containers.is_empty());

        let focused = mux.get_focused("nexus-test");
        assert!(focused.is_some());

        let dims = mux.get_dimensions(&containers[0].handle);
        assert!(dims.width > 0);
        assert!(dims.height > 0);

        mux.teardown("nexus-test");
    }

    #[test]
    #[ignore = "requires tmux to be installed and available"]
    fn integration_split_and_swap() {
        let mut mux = TmuxMux::with_socket("nexus_test_split");
        mux.initialize("nexus-split-test", "/tmp");

        let focused = mux.get_focused("nexus-split-test").unwrap();
        let new_pane = mux.split(&focused, SplitDirection::Horizontal, None, "/tmp");
        assert!(!new_pane.is_empty());

        let containers = mux.list_containers("nexus-split-test");
        assert!(containers.len() >= 2);

        assert!(mux.container_exists(&new_pane));
        assert!(mux.swap_containers(&focused, &new_pane));

        mux.teardown("nexus-split-test");
    }
}
