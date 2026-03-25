# Session Persistence — Design Spec

## Goal

Enable Nexus to save and restore workspace state across daemon restarts, and export/import reusable layout templates. Two distinct persistence concepts: **workspace saves** (full runtime state) and **layout exports** (reusable pane geometry templates).

## Architecture

### Two Persistence Concepts

| Concept | What it stores | Where it lives | Use case |
|---------|---------------|----------------|----------|
| **Workspace Save** | Layout tree + pane runtime state + stacks + focus | `~/.nexus/sessions/<name>/state.json` | "Resume where I left off" |
| **Layout Export** | Layout tree geometry + pane types only | `~/.nexus/layouts/<name>.json` (global) or `<project>/.nexus/layouts/<name>.json` (project-local) | "Apply my 4-pane dev layout" |

### Components

| Component | Crate | File | Responsibility |
|-----------|-------|------|---------------|
| Persistence module | `nexus-engine` | `src/persistence.rs` | Serialize/deserialize NexusCore state, read/write JSON files |
| AutoSave task | `nexus-daemon` | `src/main.rs` (timer) | Periodic checkpoint every 30s when state has changed |
| Dispatch methods | `nexus-engine` | `src/dispatch.rs` | New `session.*` and `layout.*` methods |
| Client methods | `nexus-client` | `src/client.rs` | Convenience wrappers for new dispatch methods |

## Schemas

### Layout Export Format

A recursive tree matching the existing `LayoutNode` structure. Pane types only, no runtime state:

```json
{
  "name": "dev-standard",
  "description": "4-pane dev layout",
  "root": {
    "type": "Split",
    "direction": "Horizontal",
    "ratio": 0.25,
    "left": { "type": "Leaf", "id": "p0", "pane_type": "Explorer" },
    "right": {
      "type": "Split",
      "direction": "Vertical",
      "ratio": 0.7,
      "left": {
        "type": "Split",
        "direction": "Horizontal",
        "ratio": 0.6,
        "left": { "type": "Leaf", "id": "p1", "pane_type": "Editor" },
        "right": { "type": "Leaf", "id": "p2", "pane_type": "Chat" }
      },
      "right": { "type": "Leaf", "id": "p3", "pane_type": "Terminal" }
    }
  }
}
```

This is the exact serde output of `LayoutNode` (which already derives `Serialize, Deserialize` with `#[serde(tag = "type")]`). No custom schema needed — just serialize the tree directly.

On import, leaf `id` fields are regenerated (they're workspace-specific). Only the tree structure and `pane_type` values are used.

### Workspace Save Format

Full snapshot including runtime state:

```json
{
  "version": 1,
  "name": "nexus-shell",
  "cwd": "/Users/Shared/Projects/nexus-shell",
  "timestamp": "2026-03-25T10:30:00Z",
  "layout": { /* LayoutNode tree — same as export format */ },
  "panes": {
    "p0": {
      "pane_type": "Terminal",
      "cwd": "/Users/Shared/Projects/nexus-shell/crates",
      "command": "/bin/zsh",
      "args": []
    },
    "p1": {
      "pane_type": "Editor",
      "cwd": "/Users/Shared/Projects/nexus-shell"
    }
  },
  "stacks": { /* serialized StackManager — already Serialize */ },
  "focused_pane": "p0"
}
```

The `panes` map holds per-pane runtime metadata not captured by the layout tree. On restore, the engine rebuilds the layout, then spawns PTYs and adapters based on each pane's recorded state.

### Workspace Save Struct

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkspaceSave {
    pub version: u32,
    pub name: String,
    pub cwd: String,
    pub timestamp: String,
    pub layout: LayoutTree,  // Full tree including focused, zoomed, next_id
    pub panes: HashMap<String, PaneState>,
    pub stacks: StackManager,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaneState {
    pub pane_type: PaneType,
    pub cwd: Option<String>,
    pub command: Option<String>,
    pub args: Vec<String>,
}
```

**Note:** `layout` is `LayoutTree` (not `LayoutNode`) so that `focused`, `zoomed`, and `next_id` are preserved. The separate `focused_pane` field is unnecessary since `LayoutTree.focused` already carries it.

### Layout Export Struct

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayoutExport {
    pub name: String,
    pub description: Option<String>,
    pub root: LayoutNode,
}
```

### Surface Modes and Persistence

Surface mode is a property of each **client connection**, not the workspace. Multiple surfaces can connect simultaneously to the same daemon. The workspace save is surface-agnostic — it captures logical state only.

Five surface types connect to the daemon:

| Surface | Rendering | How it uses the layout tree |
|---------|-----------|---------------------------|
| **Shell (single)** | User's terminal | Ignores layout — commands return to stdout |
| **Shell (multi)** | tmux / iTerm2 / Ghostty / OS WM | Mux adapter maps logical tree to physical panes |
| **Tauri (app)** | Internal tiling WM, one window | Split ratios rendered directly |
| **Tauri (WM)** | OS window manager (Sway/Hyprland) | Each pane = OS window, WM positions them |
| **Headless** | None | Daemon runs for agents/CI/scripts, no rendering |

On restore, each connected surface interprets the logical layout according to its own rendering model. The daemon doesn't dictate how panes are displayed — it only owns the logical structure, pane state, and PTYs.

## File Locations

```
~/.nexus/
  sessions/
    <workspace-name>/
      state.json          # latest auto-save checkpoint
      snapshots/
        <snapshot-name>.json  # named snapshots
  layouts/
    <name>.json           # global layout templates

<project>/.nexus/
  layouts/
    <name>.json           # project-local layout templates (git-trackable)
```

## Dispatch Methods

### Session Domain

| Method | Params | Returns | Description |
|--------|--------|---------|-------------|
| `session.save` | `{ "name": "snapshot-name" }` (required) | `{ "path": "..." }` | Save named snapshot to `snapshots/<name>.json`. Auto-save checkpoint (`state.json`) is managed by the daemon timer, not this method. |
| `session.restore` | `{ "name": "snapshot-name" }` | `{ "status": "ok" }` | Restore from named snapshot |
| `session.delete` | `{ "name": "snapshot-name" }` | `{ "status": "ok" }` | Delete a named snapshot |
| `session.list` | `{}` | `[{ "name", "timestamp", "cwd" }]` | List available snapshots |
| `session.info` | `{}` | `{ "name", "cwd", ... }` | Already exists — no change |

### Layout Domain

| Method | Params | Returns | Description |
|--------|--------|---------|-------------|
| `layout.export` | `{ "name": "...", "description": "...", "scope": "global"\|"project" }` | `{ "path": "..." }` | Export current layout as template. `scope` defaults to `"global"` (`~/.nexus/layouts/`); `"project"` saves to `<cwd>/.nexus/layouts/`. |
| `layout.import` | `{ "name": "..." }` | `{ "status": "ok" }` | Apply a layout template (rebuilds pane tree). Searches project-local first, then global. |
| `layout.list` | `{}` | `[{ "name", "source": "global"\|"project" }]` | List available templates (project-local + global) |
| `layout.show` | `{}` | `{ ... }` | Already exists — no change |

## AutoSave Mechanism

### Dirty Flag

`NexusCore` gains a `dirty: AtomicBool` field (or plain `bool` behind the existing `StdMutex`), set `true` on any state-mutating operation (stack ops, layout changes, PTY spawn/kill). The auto-save timer checks this flag.

### Daemon Timer

```rust
// In nexus-daemon main.rs, added to tokio::select!
_ = auto_save_loop(core.clone()) => {}
```

The loop runs every 30 seconds:
1. Lock the mutex, check `core.dirty`
2. If dirty: clone `layout` + `stacks` + pane metadata (cheap), clear dirty flag, release lock
3. Serialize the cloned snapshot and write to `~/.nexus/sessions/<name>/state.json` **outside the lock** (avoids blocking client requests during disk I/O)
4. If not dirty: release lock, no-op

### Restore on Startup

When the daemon starts with a workspace name:
1. Check `~/.nexus/sessions/<name>/state.json`
2. If exists and valid:
   - Create a fresh `NexusCore` (with mux, registry, bus, pty manager — these are not serialized)
   - Apply the deserialized `LayoutTree` to `core.layout`
   - Apply the deserialized `StackManager` to `core.stacks`
   - For each `PaneState` entry: spawn PTY with saved command/cwd, or initialize adapter
   - Set session name from save
3. If missing or corrupt: start with `default_layout()` as today

## Layout Import Flow

When `layout.import` is called:
1. Load the `LayoutExport` from disk
2. Kill all existing PTYs: iterate `core.layout.root.leaf_ids()`, call `pty.kill()` for each
3. Clear all stacks: `core.stacks = StackManager::new()`
4. Replace `core.layout` with a new `LayoutTree` built from the imported root (regenerating pane IDs via `LayoutTree::from_export(root)`)
5. For each leaf: spawn default content based on `pane_type` (Terminal -> PTY with $SHELL, others -> no-op until adapters exist)
6. Set focus to first leaf

## Existing Serialization Support

These types already derive `Serialize + Deserialize`:
- `LayoutNode`, `LayoutTree`, `Direction`, `PaneType`
- `Tab`, `TabStack`, `TabStatus`
- `EventType`, `TypedEvent`

The `StackManager` struct needs `Serialize + Deserialize` added (currently missing). Its `id_counter: u32` field must be serialized explicitly so that restored managers allocate non-colliding stack IDs. On deserialize, validate that `id_counter >= max(numeric suffix of existing stack IDs) + 1`; if not, recompute it.

## Error Handling

- File I/O errors → JSON-RPC error response with message
- Corrupt/invalid JSON → error response, don't crash, log warning
- Missing session dir → create on first save
- Version mismatch → reject with error for `version != 1`; add migration logic only when version 2 is needed

## Testing Strategy

- Unit tests in `persistence.rs`: roundtrip serialize/deserialize for `WorkspaceSave` and `LayoutExport`
- Unit tests for dirty flag behavior
- Integration test: save → kill daemon → restore → verify layout matches
- Edge cases: empty workspace, workspace with no PTYs, corrupt JSON file

## Concurrency

- `session.restore` clears the dirty flag after applying state. The auto-save timer will not fire during restore because both operations require the `StdMutex` lock.
- Disk I/O (writing JSON) happens outside the lock. A concurrent `session.restore` while auto-save is writing is safe: the restore acquires the lock and applies new state; the in-flight write completes with stale data, but the next auto-save cycle will write the restored state.

## Non-Goals (for this sub-project)

- Project discovery (Wave 1, separate sub-project)
- Boot lists (Wave 1, separate sub-project)
- Config cascade (Wave 1, separate sub-project)
- Theme persistence (Wave 3)
- Undo/redo for layout changes
