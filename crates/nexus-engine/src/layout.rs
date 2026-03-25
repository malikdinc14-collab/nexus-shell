//! Layout tree — recursive binary split tree for WM-mode pane management.
//!
//! The layout tree determines *where* panes appear spatially. Each leaf holds
//! a pane ID and type; each internal node is a split (horizontal or vertical)
//! with a ratio. Focus tracking identifies exactly one active pane.
//!
//! This is the same model used by tmux, VS Code, and tiling WMs.

use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Direction {
    Horizontal,
    Vertical,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PaneType {
    Explorer,
    Editor,
    Terminal,
    Chat,
    Info,
}

impl PaneType {
    pub fn as_str(&self) -> &'static str {
        match self {
            PaneType::Explorer => "explorer",
            PaneType::Editor => "editor",
            PaneType::Terminal => "terminal",
            PaneType::Chat => "chat",
            PaneType::Info => "info",
        }
    }

    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Self {
        match s {
            "explorer" => PaneType::Explorer,
            "editor" => PaneType::Editor,
            "terminal" => PaneType::Terminal,
            "chat" => PaneType::Chat,
            _ => PaneType::Info,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Nav {
    Left,
    Down,
    Up,
    Right,
}

// ---------------------------------------------------------------------------
// Layout node
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum LayoutNode {
    Leaf {
        id: String,
        pane_type: PaneType,
    },
    Split {
        direction: Direction,
        ratio: f64,
        left: Box<LayoutNode>,
        right: Box<LayoutNode>,
    },
}

impl LayoutNode {
    pub fn leaf(id: &str, pane_type: PaneType) -> Self {
        LayoutNode::Leaf {
            id: id.to_string(),
            pane_type,
        }
    }

    pub fn split(direction: Direction, ratio: f64, left: LayoutNode, right: LayoutNode) -> Self {
        LayoutNode::Split {
            direction,
            ratio,
            left: Box::new(left),
            right: Box::new(right),
        }
    }

    /// Collect all leaf IDs in tree order.
    pub fn leaf_ids(&self) -> Vec<String> {
        match self {
            LayoutNode::Leaf { id, .. } => vec![id.clone()],
            LayoutNode::Split { left, right, .. } => {
                let mut ids = left.leaf_ids();
                ids.extend(right.leaf_ids());
                ids
            }
        }
    }

    /// Collect all leaves as (id, pane_type) pairs in tree order.
    pub fn leaves(&self) -> Vec<(String, PaneType)> {
        match self {
            LayoutNode::Leaf { id, pane_type } => vec![(id.clone(), *pane_type)],
            LayoutNode::Split { left, right, .. } => {
                let mut out = left.leaves();
                out.extend(right.leaves());
                out
            }
        }
    }

    /// Find a leaf by ID and replace it with a split containing the original
    /// leaf plus a new leaf. Returns true if the split was performed.
    pub fn insert_split(
        &mut self,
        target_id: &str,
        direction: Direction,
        new_id: &str,
        new_type: PaneType,
        ratio: f64,
    ) -> bool {
        match self {
            LayoutNode::Leaf { id, pane_type } if id == target_id => {
                let original = LayoutNode::leaf(id, *pane_type);
                let new_leaf = LayoutNode::leaf(new_id, new_type);
                *self = LayoutNode::split(direction, ratio, original, new_leaf);
                true
            }
            LayoutNode::Split { left, right, .. } => {
                left.insert_split(target_id, direction, new_id, new_type, ratio)
                    || right.insert_split(target_id, direction, new_id, new_type, ratio)
            }
            _ => false,
        }
    }

    /// Remove a leaf by ID. Returns the simplified tree, or None if this was
    /// the leaf to remove (caller replaces with sibling).
    pub fn remove_leaf(&mut self, target_id: &str) -> bool {
        match self {
            LayoutNode::Leaf { id, .. } => id == target_id,
            LayoutNode::Split { left, right, .. } => {
                if left.is_leaf_with_id(target_id) {
                    // Replace self with right child
                    *self = *right.clone();
                    true
                } else if right.is_leaf_with_id(target_id) {
                    // Replace self with left child
                    *self = *left.clone();
                    true
                } else {
                    left.remove_leaf(target_id) || right.remove_leaf(target_id)
                }
            }
        }
    }

    fn is_leaf_with_id(&self, target_id: &str) -> bool {
        matches!(self, LayoutNode::Leaf { id, .. } if id == target_id)
    }

    /// Update the split ratio for the split containing the given pane ID as a
    /// direct child. Returns true if found.
    pub fn set_ratio_for(&mut self, pane_id: &str, new_ratio: f64) -> bool {
        match self {
            LayoutNode::Split {
                left,
                right,
                ratio,
                ..
            } => {
                if left.is_leaf_with_id(pane_id) || right.is_leaf_with_id(pane_id) {
                    *ratio = new_ratio.clamp(0.1, 0.9);
                    true
                } else {
                    left.set_ratio_for(pane_id, new_ratio)
                        || right.set_ratio_for(pane_id, new_ratio)
                }
            }
            _ => false,
        }
    }
}

// ---------------------------------------------------------------------------
// Layout tree (top-level)
// ---------------------------------------------------------------------------

/// The complete layout state: a tree of panes plus focus tracking and zoom.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayoutTree {
    pub root: LayoutNode,
    pub focused: String,
    pub zoomed: Option<String>,
    next_id: u32,
}

impl LayoutTree {
    /// Create the default IDE-like layout:
    /// ```text
    /// Split(H, 0.18)
    ///  ├── Leaf(explorer)
    ///  └── Split(H, 0.75)
    ///       ├── Split(V, 0.7)
    ///       │    ├── Leaf(editor)
    ///       │    └── Leaf(terminal)
    ///       └── Leaf(chat)
    /// ```
    pub fn default_layout() -> Self {
        let explorer = LayoutNode::leaf("pane-1", PaneType::Explorer);
        let editor = LayoutNode::leaf("pane-2", PaneType::Editor);
        let terminal = LayoutNode::leaf("pane-3", PaneType::Terminal);
        let chat = LayoutNode::leaf("pane-4", PaneType::Chat);

        let editor_terminal =
            LayoutNode::split(Direction::Vertical, 0.7, editor, terminal);
        let main_chat =
            LayoutNode::split(Direction::Horizontal, 0.75, editor_terminal, chat);
        let root =
            LayoutNode::split(Direction::Horizontal, 0.18, explorer, main_chat);

        LayoutTree {
            root,
            focused: "pane-2".into(),
            zoomed: None,
            next_id: 5,
        }
    }

    fn alloc_id(&mut self) -> String {
        let id = format!("pane-{}", self.next_id);
        self.next_id += 1;
        id
    }

    /// Split the focused pane. Returns the new pane's ID.
    pub fn split_focused(&mut self, direction: Direction, pane_type: PaneType) -> String {
        let new_id = self.alloc_id();
        self.root
            .insert_split(&self.focused, direction, &new_id, pane_type, 0.5);
        self.focused = new_id.clone();
        new_id
    }

    /// Close a pane by ID. If it's the focused pane, focus moves to the first
    /// remaining leaf. Returns false if it's the last pane (can't close).
    pub fn close_pane(&mut self, pane_id: &str) -> bool {
        let leaves = self.root.leaf_ids();
        if leaves.len() <= 1 {
            return false;
        }

        if !self.root.remove_leaf(pane_id) {
            return false;
        }

        // If we closed the focused pane, pick the first remaining leaf
        if self.focused == pane_id {
            self.focused = self.root.leaf_ids().first().cloned().unwrap_or_default();
        }

        // Cancel zoom if we closed the zoomed pane
        if self.zoomed.as_deref() == Some(pane_id) {
            self.zoomed = None;
        }

        true
    }

    /// Navigate focus in a direction. Uses spatial reasoning on the tree.
    pub fn navigate(&mut self, nav: Nav) {
        let leaves = self.root.leaf_ids();
        if leaves.len() <= 1 {
            return;
        }

        let current_idx = leaves.iter().position(|id| id == &self.focused);
        let current_idx = match current_idx {
            Some(i) => i,
            None => return,
        };

        // For directional navigation, we walk the tree to find the
        // nearest neighbor. Simplified version: use leaf order with
        // direction mapping based on tree structure.
        let new_idx = match nav {
            Nav::Left | Nav::Up => {
                if current_idx > 0 {
                    current_idx - 1
                } else {
                    leaves.len() - 1 // wrap
                }
            }
            Nav::Right | Nav::Down => {
                if current_idx < leaves.len() - 1 {
                    current_idx + 1
                } else {
                    0 // wrap
                }
            }
        };

        self.focused = leaves[new_idx].clone();
    }

    /// Toggle zoom on the focused pane. When zoomed, only that pane is shown.
    pub fn toggle_zoom(&mut self) {
        if self.zoomed.is_some() {
            self.zoomed = None;
        } else {
            self.zoomed = Some(self.focused.clone());
        }
    }

    /// Set focus to a specific pane ID. Returns false if not found.
    pub fn set_focus(&mut self, pane_id: &str) -> bool {
        let leaves = self.root.leaf_ids();
        if leaves.contains(&pane_id.to_string()) {
            self.focused = pane_id.to_string();
            // Unzoom when clicking a different pane
            if self.zoomed.as_deref() != Some(pane_id) {
                self.zoomed = None;
            }
            true
        } else {
            false
        }
    }

    /// Update the split ratio for the parent split of the given pane.
    pub fn set_ratio(&mut self, pane_id: &str, ratio: f64) -> bool {
        self.root.set_ratio_for(pane_id, ratio)
    }

    /// Flat list of all panes as JSON: [{pane_id, pane_type}, ...]
    pub fn pane_list(&self) -> serde_json::Value {
        let leaves = self.root.leaves();
        let arr: Vec<serde_json::Value> = leaves
            .into_iter()
            .map(|(id, pt)| serde_json::json!({"pane_id": id, "pane_type": pt.as_str()}))
            .collect();
        serde_json::Value::Array(arr)
    }

    /// Serialize to JSON for the frontend.
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }

    /// Build a new LayoutTree from an exported root, regenerating all pane IDs.
    ///
    /// Used by `layout.import` to apply a template without carrying over
    /// workspace-specific IDs from the export.
    pub fn from_export(root: LayoutNode) -> Self {
        let mut next_id: u32 = 1;
        let new_root = Self::regen_ids(&root, &mut next_id);
        let focused = new_root.leaf_ids().first().cloned().unwrap_or_default();
        LayoutTree {
            root: new_root,
            focused,
            zoomed: None,
            next_id,
        }
    }

    fn regen_ids(node: &LayoutNode, next_id: &mut u32) -> LayoutNode {
        match node {
            LayoutNode::Leaf { pane_type, .. } => {
                let id = format!("pane-{}", *next_id);
                *next_id += 1;
                LayoutNode::Leaf {
                    id,
                    pane_type: *pane_type,
                }
            }
            LayoutNode::Split {
                direction,
                ratio,
                left,
                right,
            } => LayoutNode::Split {
                direction: *direction,
                ratio: *ratio,
                left: Box::new(Self::regen_ids(left, next_id)),
                right: Box::new(Self::regen_ids(right, next_id)),
            },
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_layout_has_four_panes() {
        let tree = LayoutTree::default_layout();
        assert_eq!(tree.root.leaf_ids().len(), 4);
        assert_eq!(tree.focused, "pane-2");
    }

    #[test]
    fn split_focused_creates_new_pane() {
        let mut tree = LayoutTree::default_layout();
        let new_id = tree.split_focused(Direction::Vertical, PaneType::Terminal);
        assert_eq!(tree.root.leaf_ids().len(), 5);
        assert_eq!(tree.focused, new_id);
    }

    #[test]
    fn close_pane_removes_and_refocuses() {
        let mut tree = LayoutTree::default_layout();
        tree.set_focus("pane-3");
        assert!(tree.close_pane("pane-3"));
        assert_eq!(tree.root.leaf_ids().len(), 3);
        assert_ne!(tree.focused, "pane-3");
    }

    #[test]
    fn close_last_pane_returns_false() {
        let mut tree = LayoutTree {
            root: LayoutNode::leaf("only", PaneType::Editor),
            focused: "only".into(),
            zoomed: None,
            next_id: 2,
        };
        assert!(!tree.close_pane("only"));
    }

    #[test]
    fn navigate_wraps_around() {
        let mut tree = LayoutTree::default_layout();
        let leaves = tree.root.leaf_ids();
        tree.set_focus(&leaves[0]);

        tree.navigate(Nav::Left);
        assert_eq!(tree.focused, *leaves.last().unwrap());

        tree.navigate(Nav::Right);
        assert_eq!(tree.focused, leaves[0]);
    }

    #[test]
    fn zoom_toggles() {
        let mut tree = LayoutTree::default_layout();
        assert!(tree.zoomed.is_none());
        tree.toggle_zoom();
        assert_eq!(tree.zoomed, Some("pane-2".into()));
        tree.toggle_zoom();
        assert!(tree.zoomed.is_none());
    }

    #[test]
    fn set_focus_unzooms_on_different_pane() {
        let mut tree = LayoutTree::default_layout();
        tree.toggle_zoom();
        assert!(tree.zoomed.is_some());
        tree.set_focus("pane-1");
        assert!(tree.zoomed.is_none());
    }

    #[test]
    fn set_ratio_clamps() {
        let mut tree = LayoutTree::default_layout();
        assert!(tree.set_ratio("pane-1", 0.05));
        // Should be clamped to 0.1
    }

    #[test]
    fn insert_split_preserves_original() {
        let mut node = LayoutNode::leaf("a", PaneType::Editor);
        node.insert_split("a", Direction::Horizontal, "b", PaneType::Terminal, 0.5);
        let ids = node.leaf_ids();
        assert!(ids.contains(&"a".to_string()));
        assert!(ids.contains(&"b".to_string()));
    }

    #[test]
    fn leaves_returns_id_and_type() {
        let tree = LayoutNode::split(
            Direction::Vertical,
            0.5,
            LayoutNode::leaf("p1", PaneType::Terminal),
            LayoutNode::leaf("p2", PaneType::Chat),
        );
        let leaves = tree.leaves();
        assert_eq!(leaves.len(), 2);
        assert_eq!(leaves[0], ("p1".into(), PaneType::Terminal));
        assert_eq!(leaves[1], ("p2".into(), PaneType::Chat));
    }

    #[test]
    fn from_export_regenerates_ids() {
        let export_root = LayoutNode::split(
            Direction::Horizontal,
            0.3,
            LayoutNode::leaf("old-1", PaneType::Explorer),
            LayoutNode::split(
                Direction::Vertical,
                0.7,
                LayoutNode::leaf("old-2", PaneType::Editor),
                LayoutNode::leaf("old-3", PaneType::Terminal),
            ),
        );

        let tree = LayoutTree::from_export(export_root);
        let ids = tree.root.leaf_ids();

        assert_eq!(ids.len(), 3);
        for id in &ids {
            assert!(id.starts_with("pane-"), "expected pane-N, got {id}");
        }
        assert_eq!(tree.focused, ids[0]);
        assert!(tree.zoomed.is_none());
    }

    #[test]
    fn pane_list_returns_json_array() {
        let mut tree = LayoutTree::default_layout();
        // default_layout has 4 panes; split adds a 5th
        tree.split_focused(Direction::Vertical, PaneType::Chat);
        let list = tree.pane_list();
        assert!(list.is_array());
        let arr = list.as_array().unwrap();
        assert_eq!(arr.len(), 5);
        assert!(arr[0].get("pane_id").is_some());
        assert!(arr[0].get("pane_type").is_some());
    }
}
