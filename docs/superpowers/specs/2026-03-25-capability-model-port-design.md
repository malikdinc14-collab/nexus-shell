# Capability Model Port — Design Spec

> Port the Python capability model to Rust. Move tool logic out of surfaces into the engine. Make surfaces thin IPC bridges.

## Context

The Python codebase has a working capability model: abstract base classes, adapter registry with priority ranking, action dispatch, and keymap cascade. The Rust port skipped all of this — `agent.rs` and `pty.rs` live in `nexus-tauri` (a surface), violating the invariant that surfaces never own tools.

This spec corrects that by porting the capability model into `nexus-core` (traits) and `nexus-engine` (registry, dispatch, process ownership).

## Architecture

```
Surface (Tauri / tmux / sway / web)
    |  render + forward input
    v
Engine (nexus-engine) — embedded in daemon or Tauri
    |  registry.best_chat() → adapter → tool
    v
Capability Adapters → Tools (claude, nvim, yazi, PTYs)
```

**Deployment model (approach C):** Tauri embeds `NexusCore` in-process (zero IPC overhead for its own UI) AND exposes the unix socket so CLI/tmux/other surfaces can connect. Standalone `nexus-daemon` serves the same socket when no GUI is running. Same protocol, same client library.

## Capability Traits (`nexus-core/src/capability.rs`)

All traits live in `nexus-core` so adapter crates never depend on `nexus-engine`.

### Base types

```rust
use serde::{Deserialize, Serialize};
use crate::error::NexusError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CapabilityType {
    Multiplexer,
    Editor,
    Chat,
    Explorer,
}

#[derive(Debug, Clone)]
pub struct AdapterManifest {
    pub name: &'static str,
    pub capability_type: CapabilityType,
    pub priority: u32,
    pub binary: &'static str,
}

pub trait Capability: Send + Sync {
    fn manifest(&self) -> &AdapterManifest;
    fn is_available(&self) -> bool;
}
```

### Chat capability

```rust
use std::sync::mpsc;

pub enum ChatEvent {
    Start { backend: String },
    Text { chunk: String, full_text: String },
    Done { exit_code: i32, full_text: String },
    Error { message: String },
}

pub trait ChatCapability: Capability {
    /// Spawn the agent CLI and return a receiver for streaming events.
    /// The engine owns the child process lifetime.
    fn send_message(
        &self,
        message: &str,
        cwd: &str,
    ) -> Result<mpsc::Receiver<ChatEvent>, NexusError>;

    /// For mux-hosted surfaces (tmux): return the shell command to launch
    /// the agent interactively in a pane. None if not supported.
    fn get_launch_command(&self) -> Option<String>;
}
```

### Editor capability

Replaces the existing `EditorBackend` trait in `nexus-editor`.

```rust
pub trait EditorCapability: Capability {
    fn open(&mut self, path: &str, line: u32, col: u32) -> Result<(), NexusError>;
    fn get_current_buffer(&self) -> Option<String>;
    fn get_buffer_content(&self, max_lines: u32) -> Option<String>;
    fn send_command(&mut self, cmd: &str) -> Result<(), NexusError>;
    fn is_alive(&self) -> bool;
}
```

### Explorer capability

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirEntry {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub size: u64,
}

pub trait ExplorerCapability: Capability {
    fn list_directory(&self, path: &str) -> Result<Vec<DirEntry>, NexusError>;
    fn get_selection(&self) -> Option<String>;
    fn get_launch_command(&self) -> Option<String>;
}
```

### Multiplexer capability

Already exists as the `Mux` trait in `nexus-core/src/mux.rs`. No changes needed — it already defines the full contract (25 required methods + optional rendering methods).

## Capability Registry (`nexus-engine/src/registry.rs`)

```rust
pub struct CapabilityRegistry {
    chat: Vec<Box<dyn ChatCapability>>,
    editor: Vec<Box<dyn EditorCapability>>,
    explorer: Vec<Box<dyn ExplorerCapability>>,
}
```

Methods:
- `register_chat/editor/explorer(adapter)` — add adapter to the registry
- `best_chat/editor/explorer() -> Option<&dyn T>` — filter `is_available()`, sort by `manifest().priority` descending, return first
- `list_chat/editor/explorer() -> &[Box<dyn T>]` — all registered (for UI enumeration)

Auto-discovery: the embedding binary (Tauri or daemon) constructs adapters and registers them at startup. No dynamic loading.

## Adapter Locations

| Adapter | Crate | Implements | Dependencies |
|---|---|---|---|
| `ClaudeAdapter` | `nexus-core` | `ChatCapability` | std only (process spawning, PATH resolution) |
| `OpenCodeAdapter` | `nexus-core` | `ChatCapability` | std only |
| `NeovimAdapter` | `nexus-editor` | `EditorCapability` | `nvim-rs` (later) |
| `NullEditor` | `nexus-editor` | `EditorCapability` | none |
| `TmuxMux` | `nexus-tmux` | `Mux` | std (subprocess) |
| `NullMux` | `nexus-core` | `Mux` | none |
| `FsExplorer` | `nexus-core` | `ExplorerCapability` | std::fs |

Chat adapters live in `nexus-core` because they have no external deps — just process spawning with PATH resolution. This mirrors `ClaudeCodeAdapter` in Python which only uses `subprocess` and `shutil.which`.

## NexusCore Changes (`nexus-engine/src/core.rs`)

```rust
pub struct NexusCore {
    pub mux: Box<dyn Mux>,
    pub registry: CapabilityRegistry,  // NEW
    pub stacks: StackManager,
    pub bus: EventBus,
    pub layout: LayoutTree,
    pub pty: PtyManager,               // NEW — moved from nexus-tauri
    session: Option<String>,
}
```

New engine methods:
- `chat_send(pane_id, message, cwd)` — gets `registry.best_chat()`, calls `send_message()`, wires the receiver to the event bus
- `pty_spawn(pane_id, cmd, cwd)` — creates PTY via `PtyManager`, wires output to event bus
- `pty_write(pane_id, data)` — forwards input to PTY
- `pty_resize(pane_id, cols, rows)` — resizes PTY

## PTY Management (`nexus-engine/src/pty.rs`)

Moved verbatim from `nexus-tauri/src/pty.rs`. The only change: instead of emitting Tauri events directly, it pushes output through the event bus. The surface (Tauri, daemon socket, etc.) subscribes to bus events and forwards them to its client.

`portable-pty` dependency moves from `nexus-tauri/Cargo.toml` to `nexus-engine/Cargo.toml`.

## What Leaves `nexus-tauri`

| File | Action |
|---|---|
| `agent.rs` | **Delete.** Replaced by `ClaudeAdapter` in `nexus-core` + engine dispatch. |
| `pty.rs` | **Delete.** Moved to `nexus-engine/src/pty.rs`. |
| `commands.rs` | **Simplify.** `agent_send` → calls `core.chat_send()`. PTY commands → call `core.pty_*()`. Layout/stack commands unchanged. |
| `main.rs` | Add socket listener thread (embedded daemon mode). |

## Keymap System (`nexus-core/src/keymap.rs`)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyBinding {
    pub key: String,      // "Alt+h", "Ctrl+\\"
    pub action: String,   // "navigate.left", "pane.split.vertical"
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandEntry {
    pub id: String,       // "navigate.left"
    pub label: String,    // "Navigate Left"
    pub category: String, // "Navigation"
}
```

Functions:
- `parse_keymap(path) -> Vec<KeyBinding>` — parse `keymap.conf` (same format as Python: `Alt+h = navigate.left`)
- `load_keymap_cascade(global, profile, workspace) -> Vec<KeyBinding>` — merge with last-wins
- `default_keymap() -> Vec<KeyBinding>` — built-in defaults (the Alt+h/j/k/l etc. that are currently hardcoded)
- `command_registry() -> Vec<CommandEntry>` — all known commands with labels

Engine exposes via Tauri commands:
- `get_keymap() -> Vec<KeyBinding>`
- `get_commands() -> Vec<CommandEntry>`

Tauri UI fetches these on init and builds its keyboard handler + command palette dynamically.

## Command Dispatch (`nexus-engine/src/dispatch.rs`)

Maps `domain.action` strings to engine operations. Same pattern as Python `dispatch.py`.

```rust
pub fn dispatch(core: &mut NexusCore, command: &str, args: &HashMap<String, Value>) -> Result<Value, NexusError> {
    let (domain, action) = command.split_once('.').ok_or(NexusError::InvalidState("bad command format".into()))?;
    match domain {
        "navigate" => handle_navigate(core, action, args),
        "pane" => handle_pane(core, action, args),
        "editor" => handle_editor(core, action, args),
        "chat" => handle_chat(core, action, args),
        "stack" => handle_stack(core, action, args),
        _ => Err(NexusError::NotFound(format!("unknown domain: {domain}"))),
    }
}
```

This is the single entry point for all commands — CLI, Tauri IPC, daemon socket protocol, and tmux keybinds all route through here.

## Dependency Graph (After)

```
nexus-core (traits, shared types, simple adapters)
├── ChatCapability, EditorCapability, ExplorerCapability, Mux
├── ClaudeAdapter, OpenCodeAdapter, FsExplorer
├── KeyBinding, CommandEntry, keymap parser
├── AdapterManifest, CapabilityType
├── NexusError, NexusConfig, constants

nexus-engine (orchestration, state, process ownership)
├── nexus-core
├── CapabilityRegistry
├── NexusCore (mux + registry + stacks + bus + layout + pty)
├── PtyManager (moved from nexus-tauri)
├── dispatch (domain.action routing)
├── portable-pty

nexus-editor (editor adapters)
├── nexus-core
├── NeovimAdapter, NullEditor

nexus-tmux (mux adapter)
├── nexus-core
├── TmuxMux

nexus-tauri (thin surface)
├── nexus-engine
├── IPC bridge (commands.rs → core.dispatch())
├── Embedded socket listener
├── Window/Tauri-native concerns only

nexus-daemon (standalone daemon)
├── nexus-engine
├── Socket listener (same protocol as Tauri-embedded)

nexus-cli (client)
├── nexus-core (types only, for serialization)
├── Socket client (talks to daemon or Tauri)
```

## Invariants

1. **Surfaces never spawn tools.** All process lifecycle goes through the engine.
2. **Adapter crates depend on `nexus-core`, never `nexus-engine`.** Keeps the dependency graph clean.
3. **One command dispatch entry point.** CLI, Tauri, daemon, tmux keybinds all call `dispatch()`.
4. **One keymap format.** `keymap.conf` parsed identically everywhere. Cascade: global > profile > workspace.
5. **Registry ranks by priority.** `is_available()` filters, `manifest().priority` sorts. Highest available wins.
6. **Event bus bridges surfaces.** Engine pushes events (PTY output, chat chunks) to the bus. Surfaces subscribe and forward to their rendering layer.

## Scope

This spec covers porting the capability model only. Not in scope:
- Actual tmux subprocess calls in `TmuxMux` (stays a stub)
- Actual nvim RPC in `NeovimAdapter` (stays a stub)
- Daemon socket protocol implementation (separate spec)
- Tauri embedded socket listener (separate spec)
- Connector/event wiring system (future)
- Boot lists, vault, workspace indexing (future)
