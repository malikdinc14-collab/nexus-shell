//! Layout templates — preset layout + stack configurations.
//!
//! Templates provide a complete initial state: a layout tree plus the
//! tab names for each pane's stack. Users can boot into a template
//! or switch at any time via `layout.template`.

use crate::layout::{Direction, LayoutNode};

/// A complete layout preset with initial stack configuration.
pub struct LayoutTemplate {
    pub name: &'static str,
    pub description: &'static str,
    pub layout: LayoutNode,
    /// (pane_id, initial_tab_name) for each leaf in the layout.
    pub stacks: Vec<(&'static str, &'static str)>,
}

/// Return all built-in templates.
pub fn builtin_templates() -> Vec<LayoutTemplate> {
    vec![vscode(), obsidian(), minimal()]
}

/// Look up a template by name.
pub fn get_template(name: &str) -> Option<LayoutTemplate> {
    builtin_templates().into_iter().find(|t| t.name == name)
}

/// VS Code-like: explorer | editor/terminal | chat
fn vscode() -> LayoutTemplate {
    let explorer = LayoutNode::leaf("pane-1");
    let editor = LayoutNode::leaf("pane-2");
    let terminal = LayoutNode::leaf("pane-3");
    let chat = LayoutNode::leaf("pane-4");

    let editor_terminal = LayoutNode::split(Direction::Vertical, 0.7, editor, terminal);
    let main_chat = LayoutNode::split(Direction::Horizontal, 0.75, editor_terminal, chat);
    let root = LayoutNode::split(Direction::Horizontal, 0.18, explorer, main_chat);

    LayoutTemplate {
        name: "vscode",
        description: "IDE-like: explorer + editor/terminal + chat sidebar",
        layout: root,
        stacks: vec![
            ("pane-1", "Explorer"),
            ("pane-2", "Editor"),
            ("pane-3", "Terminal"),
            ("pane-4", "Chat"),
        ],
    }
}

/// Obsidian-like: explorer | editor | editor (dual editor)
fn obsidian() -> LayoutTemplate {
    let explorer = LayoutNode::leaf("pane-1");
    let editor_left = LayoutNode::leaf("pane-2");
    let editor_right = LayoutNode::leaf("pane-3");

    let editors = LayoutNode::split(Direction::Horizontal, 0.5, editor_left, editor_right);
    let root = LayoutNode::split(Direction::Horizontal, 0.2, explorer, editors);

    LayoutTemplate {
        name: "obsidian",
        description: "Note-taking: explorer + dual editor panes",
        layout: root,
        stacks: vec![
            ("pane-1", "Explorer"),
            ("pane-2", "Editor"),
            ("pane-3", "Editor"),
        ],
    }
}

/// Minimal: single full-screen pane
fn minimal() -> LayoutTemplate {
    LayoutTemplate {
        name: "minimal",
        description: "Single full-screen pane",
        layout: LayoutNode::leaf("pane-1"),
        stacks: vec![("pane-1", "Terminal")],
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builtin_templates_exist() {
        let templates = builtin_templates();
        assert!(templates.len() >= 3);
        assert!(get_template("vscode").is_some());
        assert!(get_template("obsidian").is_some());
        assert!(get_template("minimal").is_some());
        assert!(get_template("nonexistent").is_none());
    }

    #[test]
    fn vscode_template_has_four_panes() {
        let t = get_template("vscode").unwrap();
        assert_eq!(t.layout.leaf_ids().len(), 4);
        assert_eq!(t.stacks.len(), 4);
    }

    #[test]
    fn obsidian_template_has_three_panes() {
        let t = get_template("obsidian").unwrap();
        assert_eq!(t.layout.leaf_ids().len(), 3);
        assert_eq!(t.stacks.len(), 3);
    }

    #[test]
    fn minimal_template_has_one_pane() {
        let t = get_template("minimal").unwrap();
        assert_eq!(t.layout.leaf_ids().len(), 1);
        assert_eq!(t.stacks.len(), 1);
    }
}
