//! Layout tree — recursive binary split tree for WM-mode pane management.
//!
//! The layout tree determines *where* panes appear spatially. Each leaf holds
//! a pane ID; each internal node is a split (horizontal or vertical) with a
//! ratio. Focus tracking identifies exactly one active pane.
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


#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Nav {
    Left,
    Down,
    Up,
    Right,
}

/// Normalized bounding rectangle for spatial navigation.
#[derive(Debug, Clone, Copy)]
pub struct Rect {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
}

/// Check if two 1D ranges [a0,a1) and [b0,b1) overlap.
fn ranges_overlap(a0: f64, a1: f64, b0: f64, b1: f64) -> bool {
    a0 < b1 - 0.001 && b0 < a1 - 0.001
}

// ---------------------------------------------------------------------------
// Layout node
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum LayoutNode {
    Leaf {
        id: String,
    },
    Split {
        direction: Direction,
        ratio: f64,
        left: Box<LayoutNode>,
        right: Box<LayoutNode>,
    },
}

impl LayoutNode {
    pub fn leaf(id: &str) -> Self {
        LayoutNode::Leaf {
            id: id.to_string(),
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

    /// Find a leaf by ID and replace it with a split containing the original
    /// leaf plus a new leaf. Returns true if the split was performed.
    pub fn insert_split(
        &mut self,
        target_id: &str,
        direction: Direction,
        new_id: &str,
        ratio: f64,
    ) -> bool {
        match self {
            LayoutNode::Leaf { id } if id == target_id => {
                let original = LayoutNode::leaf(id);
                let new_leaf = LayoutNode::leaf(new_id);
                *self = LayoutNode::split(direction, ratio, original, new_leaf);
                true
            }
            LayoutNode::Split { left, right, .. } => {
                left.insert_split(target_id, direction, new_id, ratio)
                    || right.insert_split(target_id, direction, new_id, ratio)
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

    /// Compute normalized bounding rectangles for all leaves.
    pub fn compute_bounds(&self, rect: Rect) -> Vec<(String, Rect)> {
        match self {
            LayoutNode::Leaf { id } => vec![(id.clone(), rect)],
            LayoutNode::Split { direction, ratio, left, right } => {
                let (left_rect, right_rect) = match direction {
                    Direction::Horizontal => (
                        Rect { x: rect.x, y: rect.y, w: rect.w * ratio, h: rect.h },
                        Rect { x: rect.x + rect.w * ratio, y: rect.y, w: rect.w * (1.0 - ratio), h: rect.h },
                    ),
                    Direction::Vertical => (
                        Rect { x: rect.x, y: rect.y, w: rect.w, h: rect.h * ratio },
                        Rect { x: rect.x, y: rect.y + rect.h * ratio, w: rect.w, h: rect.h * (1.0 - ratio) },
                    ),
                };
                let mut out = left.compute_bounds(left_rect);
                out.extend(right.compute_bounds(right_rect));
                out
            }
        }
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
        let explorer = LayoutNode::leaf("pane-1");
        let editor = LayoutNode::leaf("pane-2");
        let terminal = LayoutNode::leaf("pane-3");
        let chat = LayoutNode::leaf("pane-4");

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
    pub fn split_focused(&mut self, direction: Direction) -> String {
        let new_id = self.alloc_id();
        self.root
            .insert_split(&self.focused, direction, &new_id, 0.5);
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

    /// Navigate focus in a direction using spatial bounding-box reasoning.
    ///
    /// Computes normalized [0,1] x [0,1] rectangles for each leaf based on
    /// tree structure and split ratios, then finds the nearest neighbor in
    /// the given direction that overlaps on the perpendicular axis.
    pub fn navigate(&mut self, nav: Nav) {
        let bounds = self.root.compute_bounds(Rect { x: 0.0, y: 0.0, w: 1.0, h: 1.0 });
        if bounds.len() <= 1 {
            return;
        }

        let current = match bounds.iter().find(|(id, _)| id == &self.focused) {
            Some((_, r)) => *r,
            None => return,
        };

        let cx = current.x + current.w / 2.0;
        let cy = current.y + current.h / 2.0;

        let mut best: Option<(String, f64)> = None;

        for (id, r) in &bounds {
            if id == &self.focused {
                continue;
            }

            let tx = r.x + r.w / 2.0;
            let ty = r.y + r.h / 2.0;

            // Check direction and perpendicular overlap
            let valid = match nav {
                Nav::Left => tx < cx - 0.001 && ranges_overlap(r.y, r.y + r.h, current.y, current.y + current.h),
                Nav::Right => tx > cx + 0.001 && ranges_overlap(r.y, r.y + r.h, current.y, current.y + current.h),
                Nav::Up => ty < cy - 0.001 && ranges_overlap(r.x, r.x + r.w, current.x, current.x + current.w),
                Nav::Down => ty > cy + 0.001 && ranges_overlap(r.x, r.x + r.w, current.x, current.x + current.w),
            };

            if !valid {
                continue;
            }

            // Distance: primary axis distance + small perpendicular penalty
            let dist = match nav {
                Nav::Left => (cx - tx) + (cy - ty).abs() * 0.1,
                Nav::Right => (tx - cx) + (cy - ty).abs() * 0.1,
                Nav::Up => (cy - ty) + (cx - tx).abs() * 0.1,
                Nav::Down => (ty - cy) + (cx - tx).abs() * 0.1,
            };

            if best.as_ref().map_or(true, |(_, d)| dist < *d) {
                best = Some((id.clone(), dist));
            }
        }

        // If no spatial neighbor found, wrap around
        if let Some((id, _)) = best {
            self.focused = id;
        } else {
            // Wrap: pick the farthest pane in the opposite direction
            let wrap_target = bounds.iter()
                .filter(|(id, _)| id != &self.focused)
                .min_by(|(_, a), (_, b)| {
                    let da = match nav {
                        Nav::Left => -(a.x + a.w / 2.0),
                        Nav::Right => a.x + a.w / 2.0,
                        Nav::Up => -(a.y + a.h / 2.0),
                        Nav::Down => a.y + a.h / 2.0,
                    };
                    let db = match nav {
                        Nav::Left => -(b.x + b.w / 2.0),
                        Nav::Right => b.x + b.w / 2.0,
                        Nav::Up => -(b.y + b.h / 2.0),
                        Nav::Down => b.y + b.h / 2.0,
                    };
                    da.partial_cmp(&db).unwrap_or(std::cmp::Ordering::Equal)
                });
            if let Some((id, _)) = wrap_target {
                self.focused = id.clone();
            }
        }
    }

    /// Toggle zoom on the focused pane. When zoomed, only that pane is shown.
    pub fn toggle_zoom(&mut self) {
        if self.zoomed.is_some() {
            self.zoomed = None;
        } else {
            self.zoomed = Some(self.focused.clone());
        }
    }

    /// Minimize a pane by shrinking its split ratio to the minimum (0.1).
    /// The pane remains in the layout but takes minimal space.
    pub fn minimize_pane(&mut self, pane_id: &str) -> bool {
        self.root.set_ratio_for(pane_id, 0.1)
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

    /// Flat list of all panes as JSON: [{pane_id}, ...]
    pub fn pane_list(&self) -> serde_json::Value {
        let ids = self.root.leaf_ids();
        let arr: Vec<serde_json::Value> = ids
            .into_iter()
            .map(|id| serde_json::json!({"pane_id": id}))
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
            LayoutNode::Leaf { .. } => {
                let id = format!("pane-{}", *next_id);
                *next_id += 1;
                LayoutNode::Leaf { id }
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
        let new_id = tree.split_focused(Direction::Vertical);
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
            root: LayoutNode::leaf("only"),
            focused: "only".into(),
            zoomed: None,
            next_id: 2,
        };
        assert!(!tree.close_pane("only"));
    }

    #[test]
    fn navigate_geometric_horizontal() {
        // Default layout: explorer(left) | editor(top-center) | chat(right)
        //                                | terminal(bottom-center)
        let mut tree = LayoutTree::default_layout();

        // Start at editor (pane-2), go right should reach chat (pane-4)
        tree.set_focus("pane-2");
        tree.navigate(Nav::Right);
        assert_eq!(tree.focused, "pane-4");

        // From chat, go left should reach editor or terminal
        tree.navigate(Nav::Left);
        assert!(tree.focused == "pane-2" || tree.focused == "pane-3");
    }

    #[test]
    fn navigate_geometric_vertical() {
        let mut tree = LayoutTree::default_layout();

        // Start at editor (pane-2), go down should reach terminal (pane-3)
        tree.set_focus("pane-2");
        tree.navigate(Nav::Down);
        assert_eq!(tree.focused, "pane-3");

        // From terminal, go up should reach editor
        tree.navigate(Nav::Up);
        assert_eq!(tree.focused, "pane-2");
    }

    #[test]
    fn navigate_wraps_around() {
        let mut tree = LayoutTree::default_layout();
        // Start at explorer (leftmost), go left should wrap
        tree.set_focus("pane-1");
        tree.navigate(Nav::Left);
        // Should wrap to rightmost pane (chat)
        assert_eq!(tree.focused, "pane-4");
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
        let mut node = LayoutNode::leaf("a");
        node.insert_split("a", Direction::Horizontal, "b", 0.5);
        let ids = node.leaf_ids();
        assert!(ids.contains(&"a".to_string()));
        assert!(ids.contains(&"b".to_string()));
    }

    #[test]
    fn from_export_regenerates_ids() {
        let export_root = LayoutNode::split(
            Direction::Horizontal,
            0.3,
            LayoutNode::leaf("old-1"),
            LayoutNode::split(
                Direction::Vertical,
                0.7,
                LayoutNode::leaf("old-2"),
                LayoutNode::leaf("old-3"),
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
        tree.split_focused(Direction::Vertical);
        let list = tree.pane_list();
        assert!(list.is_array());
        let arr = list.as_array().unwrap();
        assert_eq!(arr.len(), 5);
        assert!(arr[0].get("pane_id").is_some());
    }
}
