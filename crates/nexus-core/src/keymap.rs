//! Keymap system — parser, cascade, defaults, and tmux binding generation.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyBinding {
    pub key: String,
    pub action: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandEntry {
    pub id: String,
    pub label: String,
    pub category: String,
    pub binding: Option<String>,
}

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

/// Parse `Key = domain.action` format from a string.
/// Lines beginning with `#` or that are blank/whitespace-only are skipped.
pub fn parse_keymap_str(content: &str) -> Vec<KeyBinding> {
    content
        .lines()
        .filter_map(|line| {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                return None;
            }
            let mut parts = trimmed.splitn(2, '=');
            let key = parts.next()?.trim().to_string();
            let action = parts.next()?.trim().to_string();
            if key.is_empty() || action.is_empty() {
                return None;
            }
            Some(KeyBinding { key, action })
        })
        .collect()
}

/// Read a keymap file from `path` and parse it.
/// Returns an empty `Vec` if the file is missing or unreadable.
pub fn parse_keymap(path: &str) -> Vec<KeyBinding> {
    match fs::read_to_string(path) {
        Ok(content) => parse_keymap_str(&content),
        Err(_) => Vec::new(),
    }
}

// ---------------------------------------------------------------------------
// Cascade / merge
// ---------------------------------------------------------------------------

/// Merge multiple keymap layers with last-wins semantics per key.
pub fn cascade_keymaps(layers: &[Vec<KeyBinding>]) -> Vec<KeyBinding> {
    // Use an IndexMap-like approach: preserve insertion order with override.
    let mut order: Vec<String> = Vec::new();
    let mut map: HashMap<String, String> = HashMap::new();

    for layer in layers {
        for binding in layer {
            if !map.contains_key(&binding.key) {
                order.push(binding.key.clone());
            }
            map.insert(binding.key.clone(), binding.action.clone());
        }
    }

    order
        .into_iter()
        .map(|key| {
            let action = map[&key].clone();
            KeyBinding { key, action }
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

/// Built-in default keymap.
pub fn default_keymap() -> Vec<KeyBinding> {
    parse_keymap_str(
        "\
# Navigation
Alt+h = navigate.left
Alt+j = navigate.down
Alt+k = navigate.up
Alt+l = navigate.right

# Pane management
Alt+v = pane.split.horizontal
Alt+s = pane.split.vertical
Alt+f = pane.zoom
Alt+w = pane.close
Alt+q = pane.close
Alt+- = pane.minimize

# Stack (tab) operations
Alt+n = stack.push
Alt+[ = stack.prev
Alt+] = stack.next
Alt+t = stack.list

# Pane creation
Alt+e = pane.new.explorer
Alt+c = pane.new.chat

# Module
Alt+o = stack.open

# UI
Alt+p = command_palette.toggle
Ctrl+\\ = command_line.toggle

# Display
Alt+g = display.gaps
Alt+b = display.transparent
",
    )
}

/// All known commands with labels and categories.
pub fn default_commands() -> Vec<CommandEntry> {
    vec![
        // Navigation
        CommandEntry {
            id: "navigate.left".into(),
            label: "Navigate Left".into(),
            category: "Navigation".into(),
            binding: None,
        },
        CommandEntry {
            id: "navigate.right".into(),
            label: "Navigate Right".into(),
            category: "Navigation".into(),
            binding: None,
        },
        CommandEntry {
            id: "navigate.up".into(),
            label: "Navigate Up".into(),
            category: "Navigation".into(),
            binding: None,
        },
        CommandEntry {
            id: "navigate.down".into(),
            label: "Navigate Down".into(),
            category: "Navigation".into(),
            binding: None,
        },
        // Pane
        CommandEntry {
            id: "pane.split.vertical".into(),
            label: "Split Pane Vertical".into(),
            category: "Pane".into(),
            binding: None,
        },
        CommandEntry {
            id: "pane.split.horizontal".into(),
            label: "Split Pane Horizontal".into(),
            category: "Pane".into(),
            binding: None,
        },
        CommandEntry {
            id: "pane.zoom".into(),
            label: "Zoom Pane".into(),
            category: "Pane".into(),
            binding: None,
        },
        CommandEntry {
            id: "pane.close".into(),
            label: "Close Pane".into(),
            category: "Pane".into(),
            binding: None,
        },
        CommandEntry {
            id: "pane.minimize".into(),
            label: "Minimize Pane".into(),
            category: "Pane".into(),
            binding: None,
        },
        CommandEntry {
            id: "pane.set_role".into(),
            label: "Set Pane Role...".into(),
            category: "Pane".into(),
            binding: None,
        },
        CommandEntry {
            id: "pane.clear_role".into(),
            label: "Clear Pane Role".into(),
            category: "Pane".into(),
            binding: None,
        },
        CommandEntry {
            id: "pane.new.terminal".into(),
            label: "New Terminal Pane".into(),
            category: "Pane".into(),
            binding: None,
        },
        CommandEntry {
            id: "pane.new.chat".into(),
            label: "New Chat Pane".into(),
            category: "Chat".into(),
            binding: None,
        },
        CommandEntry {
            id: "pane.new.explorer".into(),
            label: "New Explorer Pane".into(),
            category: "Pane".into(),
            binding: None,
        },
        // UI
        CommandEntry {
            id: "command_palette.toggle".into(),
            label: "Toggle Command Palette".into(),
            category: "UI".into(),
            binding: None,
        },
        CommandEntry {
            id: "command_line.toggle".into(),
            label: "Command Line".into(),
            category: "UI".into(),
            binding: None,
        },
        // Stack
        CommandEntry {
            id: "stack.push".into(),
            label: "Push to Stack".into(),
            category: "Stack".into(),
            binding: None,
        },
        CommandEntry {
            id: "stack.pop".into(),
            label: "Pop from Stack".into(),
            category: "Stack".into(),
            binding: None,
        },
        CommandEntry {
            id: "stack.prev".into(),
            label: "Previous Tab".into(),
            category: "Stack".into(),
            binding: None,
        },
        CommandEntry {
            id: "stack.next".into(),
            label: "Next Tab".into(),
            category: "Stack".into(),
            binding: None,
        },
        CommandEntry {
            id: "stack.list".into(),
            label: "Show Stack".into(),
            category: "Stack".into(),
            binding: None,
        },
        CommandEntry {
            id: "stack.open".into(),
            label: "Open Module in Pane...".into(),
            category: "Stack".into(),
            binding: None,
        },
        CommandEntry {
            id: "layout.template".into(),
            label: "Apply Layout Template...".into(),
            category: "Layout".into(),
            binding: None,
        },
        // Display
        CommandEntry {
            id: "display.gaps".into(),
            label: "Toggle Gaps".into(),
            category: "Display".into(),
            binding: None,
        },
        CommandEntry {
            id: "display.transparent".into(),
            label: "Toggle Transparency".into(),
            category: "Display".into(),
            binding: None,
        },
        // Chat
        CommandEntry {
            id: "chat.new_session".into(),
            label: "New Chat Session".into(),
            category: "Chat".into(),
            binding: None,
        },
        CommandEntry {
            id: "chat.clear".into(),
            label: "Clear Chat".into(),
            category: "Chat".into(),
            binding: None,
        },
    ]
}

// ---------------------------------------------------------------------------
// Binding population
// ---------------------------------------------------------------------------

/// Populate the `binding` field on each `CommandEntry` from the keymap.
/// The keymap is treated as action -> key (first binding wins if duplicates exist).
pub fn merge_bindings(commands: &mut [CommandEntry], keymap: &[KeyBinding]) {
    // Build action -> key map (first occurrence wins).
    let mut action_to_key: HashMap<&str, &str> = HashMap::new();
    for binding in keymap {
        action_to_key.entry(binding.action.as_str()).or_insert(binding.key.as_str());
    }

    for cmd in commands.iter_mut() {
        if let Some(&key) = action_to_key.get(cmd.id.as_str()) {
            cmd.binding = Some(key.to_string());
        }
    }
}

// ---------------------------------------------------------------------------
// Tmux binding generation
// ---------------------------------------------------------------------------

/// Convert a key specification to a tmux key name.
/// `Alt+x` -> `M-x`, `Ctrl+x` -> `C-x`, anything else passed through.
fn to_tmux_key(key: &str) -> String {
    if let Some(rest) = key.strip_prefix("Alt+") {
        format!("M-{}", rest)
    } else if let Some(rest) = key.strip_prefix("Ctrl+") {
        format!("C-{}", rest)
    } else {
        key.to_string()
    }
}

/// Generate tmux `bind-key` lines for each binding.
/// Format: `bind-key -n M-h run-shell "nexus-ctl navigate.left"`
pub fn generate_tmux_bindings(keymap: &[KeyBinding]) -> Vec<String> {
    keymap
        .iter()
        .map(|b| {
            let tmux_key = to_tmux_key(&b.key);
            format!(
                r#"bind-key -n {} run-shell "nexus-ctl {}""#,
                tmux_key, b.action
            )
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_keymap_line() {
        let bindings = parse_keymap_str("Alt+h = navigate.left\nAlt+j = navigate.down\n");
        assert_eq!(bindings.len(), 2);
        assert_eq!(bindings[0].key, "Alt+h");
        assert_eq!(bindings[0].action, "navigate.left");
        assert_eq!(bindings[1].key, "Alt+j");
        assert_eq!(bindings[1].action, "navigate.down");
    }

    #[test]
    fn parse_keymap_skips_comments_and_blanks() {
        let bindings = parse_keymap_str("# comment\n\nAlt+h = navigate.left\n  \n");
        assert_eq!(bindings.len(), 1);
    }

    #[test]
    fn default_keymap_is_non_empty() {
        let km = default_keymap();
        assert!(!km.is_empty());
    }

    #[test]
    fn default_keymap_has_navigation() {
        let km = default_keymap();
        let actions: Vec<&str> = km.iter().map(|b| b.action.as_str()).collect();
        assert!(actions.contains(&"navigate.left"));
        assert!(actions.contains(&"navigate.right"));
        assert!(actions.contains(&"navigate.up"));
        assert!(actions.contains(&"navigate.down"));
    }

    #[test]
    fn default_commands_are_non_empty() {
        let cmds = default_commands();
        assert!(!cmds.is_empty());
    }

    #[test]
    fn merge_bindings_populates_binding_field() {
        let mut cmds = default_commands();
        let km = default_keymap();
        merge_bindings(&mut cmds, &km);
        let nav_left = cmds.iter().find(|c| c.id == "navigate.left").unwrap();
        assert!(nav_left.binding.is_some());
        assert_eq!(nav_left.binding.as_deref(), Some("Alt+h"));
    }

    #[test]
    fn cascade_last_wins() {
        let base = parse_keymap_str("Alt+h = navigate.left\n");
        let override_km = parse_keymap_str("Alt+h = custom.action\n");
        let result = cascade_keymaps(&[base, override_km]);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].action, "custom.action");
    }

    #[test]
    fn generate_tmux_bindings_format() {
        let km = vec![KeyBinding {
            key: "Alt+h".into(),
            action: "navigate.left".into(),
        }];
        let cmds = generate_tmux_bindings(&km);
        assert_eq!(cmds.len(), 1);
        assert!(cmds[0].contains("bind-key"));
        assert!(cmds[0].contains("M-h"));
        assert!(cmds[0].contains("navigate.left"));
    }
}
