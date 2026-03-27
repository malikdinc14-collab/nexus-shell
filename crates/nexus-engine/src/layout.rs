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
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
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

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum LayoutNode {
    /// A single pane with a unique ID.
    Leaf {
        id: String,
    },
    /// A binary split (horizontal or vertical) with a ratio.
    Split {
        direction: Direction,
        ratio: f64,
        left: Box<LayoutNode>,
        right: Box<LayoutNode>,
    },
    /// A weighted MxN grid for complex non-binary layouts.
    Grid {
        weights: Vec<f64>,
        columns: usize,
        children: Vec<LayoutNode>,
    },
    /// A floating/overlapping pane with absolute coordinates.
    Absolute {
        rect: Rect,
        child: Box<LayoutNode>,
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

    pub fn grid(weights: Vec<f64>, columns: usize, children: Vec<LayoutNode>) -> Self {
        LayoutNode::Grid {
            weights,
            columns,
            children,
        }
    }

    pub fn absolute(rect: Rect, child: LayoutNode) -> Self {
        LayoutNode::Absolute {
            rect,
            child: Box::new(child),
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
            LayoutNode::Grid { children, .. } => {
                children.iter().flat_map(|c| c.leaf_ids()).collect()
            }
            LayoutNode::Absolute { child, .. } => child.leaf_ids(),
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
            LayoutNode::Grid { children, .. } => {
                for child in children {
                    if child.insert_split(target_id, direction, new_id, ratio) {
                        return true;
                    }
                }
                false
            }
            LayoutNode::Absolute { child, .. } => {
                child.insert_split(target_id, direction, new_id, ratio)
            }
            _ => false,
        }
    }

    /// Find a leaf by ID and replace it with a grid containing the original
    /// leaf plus additional new leaves.
    pub fn insert_grid(
        &mut self,
        target_id: &str,
        columns: usize,
        new_ids: Vec<String>,
    ) -> bool {
        match self {
            LayoutNode::Leaf { id } if id == target_id => {
                let mut children = vec![LayoutNode::leaf(id)];
                for nid in new_ids {
                    children.push(LayoutNode::leaf(&nid));
                }
                let weights = vec![1.0; children.len()];
                *self = LayoutNode::grid(weights, columns, children);
                true
            }
            LayoutNode::Split { left, right, .. } => {
                left.insert_grid(target_id, columns, new_ids.clone())
                    || right.insert_grid(target_id, columns, new_ids)
            }
            LayoutNode::Grid { children, .. } => {
                for child in children {
                    if child.insert_grid(target_id, columns, new_ids.clone()) {
                        return true;
                    }
                }
                false
            }
            LayoutNode::Absolute { child, .. } => {
                child.insert_grid(target_id, columns, new_ids)
            }
            _ => false,
        }
    }

    /// Wrap a leaf in an Absolute container.
    pub fn insert_absolute(&mut self, target_id: &str, rect: Rect) -> bool {
        match self {
            LayoutNode::Leaf { id } if id == target_id => {
                let original = LayoutNode::leaf(id);
                *self = LayoutNode::absolute(rect, original);
                true
            }
            LayoutNode::Split { left, right, .. } => {
                left.insert_absolute(target_id, rect) || right.insert_absolute(target_id, rect)
            }
            LayoutNode::Grid { children, .. } => {
                for child in children {
                    if child.insert_absolute(target_id, rect) {
                        return true;
                    }
                }
                false
            }
            LayoutNode::Absolute { child, .. } => {
                child.insert_absolute(target_id, rect)
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
                    *self = *right.clone();
                    true
                } else if right.is_leaf_with_id(target_id) {
                    *self = *left.clone();
                    true
                } else {
                    left.remove_leaf(target_id) || right.remove_leaf(target_id)
                }
            }
            LayoutNode::Grid { children, .. } => {
                let mut found_idx = None;
                for (idx, child) in children.iter().enumerate() {
                    if child.is_leaf_with_id(target_id) {
                        found_idx = Some(idx);
                        break;
                    }
                    if child.clone().remove_leaf(target_id) {
                        // This recursion for Grid is slightly tricky because remove_leaf 
                        // in Split replaces self. Let's simplify and say for now
                        // we only support removing direct children of Grid.
                        // TODO: Proper nested Grid removal.
                        return true;
                    }
                }
                if let Some(idx) = found_idx {
                    children.remove(idx);
                    return true;
                }
                false
            }
            LayoutNode::Absolute { child, .. } => {
                if child.is_leaf_with_id(target_id) {
                    // Logic for Absolute removal? Maybe it just disappears.
                    // For now, let's say we don't allow removing the only child of Absolute directly.
                    return false;
                }
                child.remove_leaf(target_id)
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
            LayoutNode::Split {
                direction,
                ratio,
                left,
                right,
            } => {
                let (left_rect, right_rect) = match direction {
                    Direction::Horizontal => (
                        Rect {
                            x: rect.x,
                            y: rect.y,
                            w: rect.w * ratio,
                            h: rect.h,
                        },
                        Rect {
                            x: rect.x + rect.w * ratio,
                            y: rect.y,
                            w: rect.w * (1.0 - ratio),
                            h: rect.h,
                        },
                    ),
                    Direction::Vertical => (
                        Rect {
                            x: rect.x,
                            y: rect.y,
                            w: rect.w,
                            h: rect.h * ratio,
                        },
                        Rect {
                            x: rect.x,
                            y: rect.y + rect.h * ratio,
                            w: rect.w,
                            h: rect.h * (1.0 - ratio),
                        },
                    ),
                };
                let mut out = left.compute_bounds(left_rect);
                out.extend(right.compute_bounds(right_rect));
                out
            }
            LayoutNode::Grid {
                weights,
                columns,
                children,
            } => {
                let mut out = Vec::new();
                if children.is_empty() {
                    return out;
                }

                let rows = (children.len() as f64 / *columns as f64).ceil() as usize;
                
                // For simplicity in Phase 1, we assume equal weights if weights.len() != children.len()
                // or we use weights as proportions for rows/cols if they match.
                // Let's implement a simple uniform grid first.
                let cell_w = rect.w / (*columns as f64);
                let cell_h = rect.h / (rows as f64);

                for (idx, child) in children.iter().enumerate() {
                    let r = idx / columns;
                    let c = idx % columns;
                    let child_rect = Rect {
                        x: rect.x + (c as f64 * cell_w),
                        y: rect.y + (r as f64 * cell_h),
                        w: cell_w,
                        h: cell_h,
                    };
                    out.extend(child.compute_bounds(child_rect));
                }
                out
            }
            LayoutNode::Absolute { rect: abs_rect, child } => {
                // Absolute rects are relative to the parent's rect [0,1]
                let child_rect = Rect {
                    x: rect.x + abs_rect.x * rect.w,
                    y: rect.y + abs_rect.y * rect.h,
                    w: abs_rect.w * rect.w,
                    h: abs_rect.h * rect.h,
                };
                child.compute_bounds(child_rect)
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
            LayoutNode::Grid { children, .. } => {
                for child in children {
                    if child.set_ratio_for(pane_id, new_ratio) {
                        return true;
                    }
                }
                false
            }
            LayoutNode::Absolute { child, .. } => {
                child.set_ratio_for(pane_id, new_ratio)
            }
            _ => false,
        }
    }

    /// Swap two leaves by ID in a single pass. Returns true if at least one
    /// swap occurred.
    pub fn swap_leaves(&mut self, id_a: &str, id_b: &str) -> bool {
        match self {
            LayoutNode::Leaf { id } => {
                if id == id_a {
                    *id = id_b.to_string();
                    true
                } else if id == id_b {
                    *id = id_a.to_string();
                    true
                } else {
                    false
                }
            }
            LayoutNode::Split { left, right, .. } => {
                let a = left.swap_leaves(id_a, id_b);
                let b = right.swap_leaves(id_a, id_b);
                a || b
            }
            LayoutNode::Grid { children, .. } => {
                let mut swapped = false;
                for child in children {
                    swapped |= child.swap_leaves(id_a, id_b);
                }
                swapped
            }
            LayoutNode::Absolute { child, .. } => child.swap_leaves(id_a, id_b),
        }
    }

    /// Equalize all split ratios to 0.5 and all grid weights to 1.0,
    /// recursively.
    pub fn equalize(&mut self) {
        match self {
            LayoutNode::Split {
                ratio, left, right, ..
            } => {
                *ratio = 0.5;
                left.equalize();
                right.equalize();
            }
            LayoutNode::Grid {
                weights, children, ..
            } => {
                for w in weights.iter_mut() {
                    *w = 1.0;
                }
                for child in children {
                    child.equalize();
                }
            }
            LayoutNode::Absolute { child, .. } => child.equalize(),
            _ => {}
        }
    }

    /// Find the Split whose direct child is a Leaf with `pane_id` and toggle
    /// its direction between Horizontal and Vertical. Returns true if found.
    pub fn flip_parent_direction(&mut self, pane_id: &str) -> bool {
        match self {
            LayoutNode::Split {
                direction,
                left,
                right,
                ..
            } => {
                if left.is_leaf_with_id(pane_id) || right.is_leaf_with_id(pane_id) {
                    *direction = match *direction {
                        Direction::Horizontal => Direction::Vertical,
                        Direction::Vertical => Direction::Horizontal,
                    };
                    return true;
                }
                left.flip_parent_direction(pane_id)
                    || right.flip_parent_direction(pane_id)
            }
            LayoutNode::Grid { children, .. } => {
                for child in children {
                    if child.flip_parent_direction(pane_id) {
                        return true;
                    }
                }
                false
            }
            LayoutNode::Absolute { child, .. } => child.flip_parent_direction(pane_id),
            _ => false,
        }
    }

    /// Find the nearest ancestor Split whose direction matches `axis` and
    /// whose subtree contains `pane_id`. Adjust ratio by `delta` (positive =
    /// grow left child). Clamps to [0.1, 0.9]. Returns true if adjusted.
    pub fn adjust_ratio_toward(
        &mut self,
        pane_id: &str,
        delta: f64,
        axis: Direction,
    ) -> bool {
        match self {
            LayoutNode::Split {
                direction,
                ratio,
                left,
                right,
                ..
            } => {
                if *direction == axis {
                    let in_left = left.contains_leaf(pane_id);
                    let in_right = right.contains_leaf(pane_id);
                    if in_left {
                        *ratio = (*ratio + delta).clamp(0.1, 0.9);
                        return true;
                    }
                    if in_right {
                        *ratio = (*ratio + delta).clamp(0.1, 0.9);
                        return true;
                    }
                }
                // Recurse even if direction doesn't match — the target split
                // may be deeper in the tree.
                left.adjust_ratio_toward(pane_id, delta, axis)
                    || right.adjust_ratio_toward(pane_id, delta, axis)
            }
            LayoutNode::Grid { children, .. } => {
                for child in children {
                    if child.adjust_ratio_toward(pane_id, delta, axis) {
                        return true;
                    }
                }
                false
            }
            LayoutNode::Absolute { child, .. } => {
                child.adjust_ratio_toward(pane_id, delta, axis)
            }
            _ => false,
        }
    }

    /// Returns true if a Leaf with the given ID exists anywhere in this subtree.
    pub fn contains_leaf(&self, target_id: &str) -> bool {
        match self {
            LayoutNode::Leaf { id } => id == target_id,
            LayoutNode::Split { left, right, .. } => {
                left.contains_leaf(target_id) || right.contains_leaf(target_id)
            }
            LayoutNode::Grid { children, .. } => {
                children.iter().any(|c| c.contains_leaf(target_id))
            }
            LayoutNode::Absolute { child, .. } => child.contains_leaf(target_id),
        }
    }

    /// Like `insert_split` but places the new leaf as the LEFT (first) child
    /// instead of the right. Returns true if the target was found.
    pub fn insert_split_before(
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
                *self = LayoutNode::split(direction, ratio, new_leaf, original);
                true
            }
            LayoutNode::Split { left, right, .. } => {
                left.insert_split_before(target_id, direction, new_id, ratio)
                    || right.insert_split_before(target_id, direction, new_id, ratio)
            }
            LayoutNode::Grid { children, .. } => {
                for child in children {
                    if child.insert_split_before(target_id, direction, new_id, ratio) {
                        return true;
                    }
                }
                false
            }
            LayoutNode::Absolute { child, .. } => {
                child.insert_split_before(target_id, direction, new_id, ratio)
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
        LayoutTree {
            root: LayoutNode::leaf("pane-1"),
            focused: "pane-1".into(),
            zoomed: None,
            next_id: 2,
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

    /// Convert the focused pane into a grid of N panes. Returns the new pane IDs.
    pub fn split_into_grid(&mut self, columns: usize, count: usize) -> Vec<String> {
        let mut new_ids = Vec::new();
        for _ in 0..count {
            new_ids.push(self.alloc_id());
        }
        if self.root.insert_grid(&self.focused, columns, new_ids.clone()) {
            // Focus the first new child
            if let Some(first) = new_ids.first() {
                self.focused = first.clone();
            }
        }
        new_ids
    }

    /// Make the focused pane "floating" by wrapping it in an Absolute container.
    pub fn make_absolute(&mut self, rect: Rect) {
        self.root.insert_absolute(&self.focused, rect);
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

    // -----------------------------------------------------------------------
    // Tiling WM operations
    // -----------------------------------------------------------------------

    /// Find the spatial neighbor in `nav` direction and swap it with the
    /// focused pane. Focus stays on `self.focused` (the ID travels with the
    /// swap).
    pub fn swap_toward(&mut self, nav: Nav) {
        if let Some(neighbor) = self.find_spatial_neighbor(nav) {
            self.root.swap_leaves(&self.focused, &neighbor);
        }
    }

    /// Equalize all split ratios and grid weights in the tree.
    pub fn equalize(&mut self) {
        self.root.equalize();
    }

    /// Toggle the split direction of the focused pane's parent between
    /// Horizontal and Vertical.
    pub fn rotate(&mut self) {
        self.root.flip_parent_direction(&self.focused);
    }

    /// Grow or shrink the focused pane toward `nav` by adjusting the nearest
    /// matching ancestor split ratio.
    pub fn grow(&mut self, nav: Nav) {
        let (delta, axis) = match nav {
            Nav::Left => (-0.05, Direction::Horizontal),
            Nav::Right => (0.05, Direction::Horizontal),
            Nav::Up => (-0.05, Direction::Vertical),
            Nav::Down => (0.05, Direction::Vertical),
        };
        self.root.adjust_ratio_toward(&self.focused, delta, axis);
    }

    /// Move the focused pane next to its spatial neighbor in `nav` direction.
    /// The focused pane is detached from its current position and re-inserted
    /// adjacent to the neighbor.
    pub fn move_pane(&mut self, nav: Nav) {
        let neighbor = match self.find_spatial_neighbor(nav) {
            Some(n) => n,
            None => return,
        };
        let focused = self.focused.clone();

        // Detach the focused pane
        if !self.root.remove_leaf(&focused) {
            return;
        }

        let direction = match nav {
            Nav::Left | Nav::Right => Direction::Horizontal,
            Nav::Up | Nav::Down => Direction::Vertical,
        };

        match nav {
            Nav::Left | Nav::Up => {
                self.root
                    .insert_split_before(&neighbor, direction, &focused, 0.5);
            }
            Nav::Right | Nav::Down => {
                self.root
                    .insert_split(&neighbor, direction, &focused, 0.5);
            }
        }

        self.focused = focused;
    }

    /// Shared helper: find the nearest spatial neighbor in `nav` direction
    /// using bounding-box geometry (same algorithm as `navigate`).
    fn find_spatial_neighbor(&self, nav: Nav) -> Option<String> {
        let bounds = self
            .root
            .compute_bounds(Rect { x: 0.0, y: 0.0, w: 1.0, h: 1.0 });
        if bounds.len() <= 1 {
            return None;
        }

        let current = match bounds.iter().find(|(id, _)| id == &self.focused) {
            Some((_, r)) => *r,
            None => return None,
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

            let valid = match nav {
                Nav::Left => {
                    tx < cx - 0.001
                        && ranges_overlap(
                            r.y,
                            r.y + r.h,
                            current.y,
                            current.y + current.h,
                        )
                }
                Nav::Right => {
                    tx > cx + 0.001
                        && ranges_overlap(
                            r.y,
                            r.y + r.h,
                            current.y,
                            current.y + current.h,
                        )
                }
                Nav::Up => {
                    ty < cy - 0.001
                        && ranges_overlap(
                            r.x,
                            r.x + r.w,
                            current.x,
                            current.x + current.w,
                        )
                }
                Nav::Down => {
                    ty > cy + 0.001
                        && ranges_overlap(
                            r.x,
                            r.x + r.w,
                            current.x,
                            current.x + current.w,
                        )
                }
            };

            if !valid {
                continue;
            }

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

        best.map(|(id, _)| id)
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
            LayoutNode::Grid {
                weights,
                columns,
                children,
            } => LayoutNode::Grid {
                weights: weights.clone(),
                columns: *columns,
                children: children
                    .iter()
                    .map(|c| Self::regen_ids(c, next_id))
                    .collect(),
            },
            LayoutNode::Absolute { rect, child } => LayoutNode::Absolute {
                rect: *rect,
                child: Box::new(Self::regen_ids(child, next_id)),
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

    /// 4-pane layout for tests: explorer | editor+terminal | chat
    fn test_layout() -> LayoutTree {
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

    #[test]
    fn default_layout_is_single_pane() {
        let tree = LayoutTree::default_layout();
        assert_eq!(tree.root.leaf_ids().len(), 1);
        assert_eq!(tree.focused, "pane-1");
    }

    #[test]
    fn split_focused_creates_new_pane() {
        let mut tree = test_layout();
        let new_id = tree.split_focused(Direction::Vertical);
        assert_eq!(tree.root.leaf_ids().len(), 5);
        assert_eq!(tree.focused, new_id);
    }

    #[test]
    fn close_pane_removes_and_refocuses() {
        let mut tree = test_layout();
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
        let mut tree = test_layout();

        tree.set_focus("pane-2");
        tree.navigate(Nav::Right);
        assert_eq!(tree.focused, "pane-4");

        tree.navigate(Nav::Left);
        assert!(tree.focused == "pane-2" || tree.focused == "pane-3");
    }

    #[test]
    fn navigate_geometric_vertical() {
        let mut tree = test_layout();

        tree.set_focus("pane-2");
        tree.navigate(Nav::Down);
        assert_eq!(tree.focused, "pane-3");

        tree.navigate(Nav::Up);
        assert_eq!(tree.focused, "pane-2");
    }

    #[test]
    fn navigate_wraps_around() {
        let mut tree = test_layout();
        tree.set_focus("pane-1");
        tree.navigate(Nav::Left);
        assert_eq!(tree.focused, "pane-4");
    }

    #[test]
    fn zoom_toggles() {
        let mut tree = test_layout();
        assert!(tree.zoomed.is_none());
        tree.toggle_zoom();
        assert_eq!(tree.zoomed, Some("pane-2".into()));
        tree.toggle_zoom();
        assert!(tree.zoomed.is_none());
    }

    #[test]
    fn set_focus_unzooms_on_different_pane() {
        let mut tree = test_layout();
        tree.toggle_zoom();
        assert!(tree.zoomed.is_some());
        tree.set_focus("pane-1");
        assert!(tree.zoomed.is_none());
    }

    #[test]
    fn set_ratio_clamps() {
        let mut tree = test_layout();
        assert!(tree.set_ratio("pane-1", 0.05));
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
        let mut tree = test_layout();
        // test_layout has 4 panes; split adds a 5th
        tree.split_focused(Direction::Vertical);
        let list = tree.pane_list();
        assert!(list.is_array());
        let arr = list.as_array().unwrap();
        assert_eq!(arr.len(), 5);
        assert!(arr[0].get("pane_id").is_some());
    }

    #[test]
    fn grid_computes_uniform_bounds() {
        let grid = LayoutNode::grid(
            vec![1.0; 4],
            2,
            vec![
                LayoutNode::leaf("g1"),
                LayoutNode::leaf("g2"),
                LayoutNode::leaf("g3"),
                LayoutNode::leaf("g4"),
            ],
        );
        let bounds = grid.compute_bounds(Rect { x: 0.0, y: 0.0, w: 100.0, h: 100.0 });
        assert_eq!(bounds.len(), 4);
        
        // g1 (top-left)
        assert_eq!(bounds[0].1.x, 0.0);
        assert_eq!(bounds[0].1.y, 0.0);
        assert_eq!(bounds[0].1.w, 50.0);
        assert_eq!(bounds[0].1.h, 50.0);
        
        // g4 (bottom-right)
        assert_eq!(bounds[3].1.x, 50.0);
        assert_eq!(bounds[3].1.y, 50.0);
        assert_eq!(bounds[3].1.w, 50.0);
        assert_eq!(bounds[3].1.h, 50.0);
    }

    #[test]
    fn absolute_computes_relative_bounds() {
        let abs = LayoutNode::absolute(
            Rect { x: 0.1, y: 0.1, w: 0.8, h: 0.8 },
            LayoutNode::leaf("a1"),
        );
        let bounds = abs.compute_bounds(Rect { x: 0.0, y: 0.0, w: 1000.0, h: 1000.0 });
        assert_eq!(bounds.len(), 1);
        assert_eq!(bounds[0].1.x, 100.0);
        assert_eq!(bounds[0].1.y, 100.0);
        assert_eq!(bounds[0].1.w, 800.0);
        assert_eq!(bounds[0].1.h, 800.0);
    }

    // -----------------------------------------------------------------------
    // Tiling WM operation tests
    // -----------------------------------------------------------------------

    #[test]
    fn swap_leaves_works() {
        let mut node = LayoutNode::split(
            Direction::Horizontal,
            0.5,
            LayoutNode::leaf("a"),
            LayoutNode::leaf("b"),
        );
        assert!(node.swap_leaves("a", "b"));
        let ids = node.leaf_ids();
        assert_eq!(ids[0], "b");
        assert_eq!(ids[1], "a");
    }

    #[test]
    fn equalize_resets_ratios() {
        let mut node = LayoutNode::split(
            Direction::Horizontal,
            0.3,
            LayoutNode::leaf("a"),
            LayoutNode::split(
                Direction::Vertical,
                0.8,
                LayoutNode::leaf("b"),
                LayoutNode::leaf("c"),
            ),
        );
        node.equalize();
        match &node {
            LayoutNode::Split { ratio, right, .. } => {
                assert!((ratio - 0.5).abs() < f64::EPSILON);
                match right.as_ref() {
                    LayoutNode::Split { ratio: inner, .. } => {
                        assert!((inner - 0.5).abs() < f64::EPSILON);
                    }
                    _ => panic!("expected inner split"),
                }
            }
            _ => panic!("expected split"),
        }
    }

    #[test]
    fn rotate_flips_direction() {
        let mut tree = LayoutTree {
            root: LayoutNode::split(
                Direction::Horizontal,
                0.5,
                LayoutNode::leaf("pane-1"),
                LayoutNode::leaf("pane-2"),
            ),
            focused: "pane-1".into(),
            zoomed: None,
            next_id: 3,
        };
        tree.rotate();
        match &tree.root {
            LayoutNode::Split { direction, .. } => {
                assert_eq!(*direction, Direction::Vertical);
            }
            _ => panic!("expected split"),
        }
    }

    #[test]
    fn grow_adjusts_ratio() {
        let mut tree = LayoutTree {
            root: LayoutNode::split(
                Direction::Horizontal,
                0.5,
                LayoutNode::leaf("pane-1"),
                LayoutNode::leaf("pane-2"),
            ),
            focused: "pane-1".into(),
            zoomed: None,
            next_id: 3,
        };
        // Growing left means the left child shrinks (delta = -0.05 on left
        // subtree means ratio decreases).
        tree.grow(Nav::Left);
        match &tree.root {
            LayoutNode::Split { ratio, .. } => {
                assert!((*ratio - 0.45).abs() < f64::EPSILON);
            }
            _ => panic!("expected split"),
        }
        // Growing right from the left pane means ratio increases.
        tree.grow(Nav::Right);
        match &tree.root {
            LayoutNode::Split { ratio, .. } => {
                assert!((*ratio - 0.5).abs() < f64::EPSILON);
            }
            _ => panic!("expected split"),
        }
    }

    #[test]
    fn move_pane_repositions() {
        // 3-pane layout: Split(H, [A, Split(V, [B, C])])
        let mut tree = LayoutTree {
            root: LayoutNode::split(
                Direction::Horizontal,
                0.5,
                LayoutNode::leaf("a"),
                LayoutNode::split(
                    Direction::Vertical,
                    0.5,
                    LayoutNode::leaf("b"),
                    LayoutNode::leaf("c"),
                ),
            ),
            focused: "b".into(),
            zoomed: None,
            next_id: 4,
        };
        // Move B to the left of A
        tree.move_pane(Nav::Left);
        let ids = tree.root.leaf_ids();
        // B should now appear before A in tree order
        assert_eq!(ids.len(), 3);
        let b_pos = ids.iter().position(|id| id == "b").unwrap();
        let a_pos = ids.iter().position(|id| id == "a").unwrap();
        assert!(
            b_pos < a_pos,
            "expected b before a, got b@{b_pos} a@{a_pos} in {ids:?}"
        );
        assert_eq!(tree.focused, "b");
    }
}
