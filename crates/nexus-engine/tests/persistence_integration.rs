//! Integration test: full save -> restore roundtrip.

use nexus_engine::persistence;
use nexus_engine::{Direction, LayoutTree, StackManager};
use std::collections::HashMap;

#[test]
fn full_save_restore_roundtrip() {
    let dir = tempfile::tempdir().unwrap();
    let session_dir = dir.path().join("sessions").join("roundtrip");

    let mut layout = LayoutTree::default_layout();
    layout.split_focused(Direction::Vertical);
    let original_ids = layout.root.leaf_ids();
    let original_focused = layout.focused.clone();

    let save = persistence::WorkspaceSave {
        version: 1,
        name: "roundtrip".to_string(),
        cwd: "/tmp/test".to_string(),
        timestamp: "2026-03-25T12:00:00Z".to_string(),
        layout: layout.clone(),
        panes: HashMap::new(),
        stacks: StackManager::new(),
    };

    persistence::save_workspace(&session_dir, &save).unwrap();

    let restored = persistence::load_workspace(&session_dir).unwrap();

    assert_eq!(restored.name, "roundtrip");
    assert_eq!(restored.cwd, "/tmp/test");
    assert_eq!(restored.layout.root.leaf_ids(), original_ids);
    assert_eq!(restored.layout.focused, original_focused);
}

#[test]
fn layout_export_import_roundtrip() {
    let dir = tempfile::tempdir().unwrap();
    let layouts_dir = dir.path().join("layouts");

    let layout = LayoutTree::default_layout();
    let export = persistence::LayoutExport {
        name: "test-layout".to_string(),
        description: Some("test".to_string()),
        root: layout.root.clone(),
    };

    persistence::save_layout_export(&layouts_dir, &export).unwrap();

    let loaded = persistence::load_layout_export(&layouts_dir, "test-layout").unwrap();
    let imported_tree = LayoutTree::from_export(loaded.root);

    assert_eq!(imported_tree.root.leaf_ids().len(), 1);
    assert_eq!(imported_tree.root.leaf_ids()[0], "pane-1");
}

#[test]
fn snapshot_crud_lifecycle() {
    let dir = tempfile::tempdir().unwrap();
    let session_dir = dir.path().join("sessions").join("lifecycle");

    let save = persistence::WorkspaceSave {
        version: 1,
        name: "lifecycle".to_string(),
        cwd: "/tmp".to_string(),
        timestamp: "2026-03-25T12:00:00Z".to_string(),
        layout: LayoutTree::default_layout(),
        panes: HashMap::new(),
        stacks: StackManager::new(),
    };

    persistence::save_snapshot(&session_dir, "snap-a", &save).unwrap();
    persistence::save_snapshot(&session_dir, "snap-b", &save).unwrap();

    let list = persistence::list_snapshots(&session_dir).unwrap();
    assert_eq!(list.len(), 2);

    persistence::delete_snapshot(&session_dir, "snap-a").unwrap();
    let list = persistence::list_snapshots(&session_dir).unwrap();
    assert_eq!(list.len(), 1);

    let loaded = persistence::load_snapshot(&session_dir, "snap-b").unwrap();
    assert_eq!(loaded.name, "lifecycle");
}
