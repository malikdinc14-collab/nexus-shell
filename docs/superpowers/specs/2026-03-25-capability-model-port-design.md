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
use std::sync::mpsc;
use crate::error::NexusError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CapabilityType {
    Multiplexer,
    Editor,
    Chat,
    Explorer,
}

/// Runtime context injected into adapters at construction time.
/// Provides resolved PATH and other environment details that
/// GUI apps (Tauri on macOS) cannot inherit from the login shell.
#[derive(Debug, Clone)]
pub struct SystemContext {
    /// Full PATH from the user's login shell.
    pub path: String,
    /// User's preferred shell.
    pub shell: String,
}

impl SystemContext {
    /// Probe the login shell for its PATH. Cached by caller.
    pub fn from_login_shell() -> Self {
        let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/zsh".into());
        let path = std::process::Command::new(&shell)
            .args(["-l", "-c", "source ~/.zshrc 2>/dev/null; printf '%s' \"$PATH\""])
            .stdin(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .output()
            .ok()
            .filter(|o| o.status.success())
            .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| std::env::var("PATH").unwrap_or_default());
        Self { path, shell }
    }

    /// Resolve a binary name to its absolute path using this context's PATH.
    pub fn resolve_binary(&self, name: &str) -> Option<String> {
        for dir in self.path.split(':') {
            let candidate = std::path::Path::new(dir).join(name);
            if candidate.is_file() {
                return Some(candidate.to_string_lossy().to_string());
            }
        }
        None
    }
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
#[derive(Debug, Clone)]
pub enum ChatEvent {
    Start { backend: String },
    Text { chunk: String },
    Done { exit_code: i32, full_text: String },
    Error { message: String },
}

/// Headless agent backend (claude, opencode, etc.)
///
/// Threading contract: `send_message` spawns a background thread that
/// pushes events to the provided `Sender`. The caller owns the `Receiver`
/// and drains it (engine wires it to the event bus). The adapter must
/// send `Done` or `Error` as the final event and then drop the sender.
pub trait ChatCapability: Capability {
    /// Spawn the agent CLI. Push streaming events to `tx`.
    /// Returns immediately — work happens on a background thread.
    fn send_message(
        &self,
        message: &str,
        cwd: &str,
        tx: mpsc::Sender<ChatEvent>,
    ) -> Result<(), NexusError>;

    /// For mux-hosted surfaces (tmux): return the shell command to launch
    /// the agent interactively in a pane. None if not supported.
    fn get_launch_command(&self) -> Option<String>;
}
```

### Editor capability

Replaces the existing `EditorBackend` trait in `nexus-editor`.

```rust
use std::collections::HashMap;

/// Text editor backend (neovim, helix, etc.)
pub trait EditorCapability: Capability {
    fn open(&mut self, path: &str, line: u32, col: u32) -> Result<(), NexusError>;
    fn get_current_buffer(&self) -> Option<String>;
    fn get_buffer_content(&self, max_lines: u32) -> Option<String>;
    fn apply_edit(&mut self, patch: &str) -> Result<(), NexusError>;
    fn get_tabs(&self) -> Vec<HashMap<String, String>>;
    fn send_command(&mut self, cmd: &str) -> Result<(), NexusError>;
    fn remote_expr(&self, expr: &str) -> Option<String>;
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

/// File explorer backend (yazi, ranger, built-in fs)
pub trait ExplorerCapability: Capability {
    fn list_directory(&self, path: &str) -> Result<Vec<DirEntry>, NexusError>;
    fn get_selection(&self) -> Option<String>;
    fn trigger_action(&mut self, action: &str, payload: &str) -> Result<(), NexusError>;
    fn get_launch_command(&self) -> Option<String>;
}
```

### Multiplexer capability

Already exists as the `Mux` trait in `nexus-core/src/mux.rs`. The `Mux` trait does NOT implement `Capability` — it is a special case. The multiplexer is always explicitly chosen at `NexusCore` construction time (not auto-discovered via registry). This is intentional: there is exactly one active mux per engine instance, passed as `Box<dyn Mux>`.

### Deferred capability types

The Python model defines `Executor` (process lifecycle) and `Menu` (interactive selection UI) capabilities. These are deferred from this spec — no Rust adapters exist for them yet. `Executor` functionality is partially covered by `PtyManager`. `Menu` will be needed when the command palette moves to engine-driven content.

## Capability Registry (`nexus-engine/src/registry.rs`)

```rust
pub struct CapabilityRegistry {
    chat: Vec<Box<dyn ChatCapability>>,
    editor: Vec<Box<dyn EditorCapability>>,
    explorer: Vec<Box<dyn ExplorerCapability>>,
    ctx: SystemContext,
}
```

Methods:
- `new(ctx: SystemContext)` — construct with resolved system context
- `register_chat/editor/explorer(adapter)` — add adapter to the registry
- `best_chat/editor/explorer() -> Option<&dyn T>` — filter `is_available()`, sort by `manifest().priority` descending, return first
- `list_chat/editor/explorer() -> &[Box<dyn T>]` — all registered (for UI enumeration)

Adding a new capability type (e.g., Menu) requires adding a new Vec field and corresponding methods. This is a deliberate trade-off: type safety over generic extensibility. Each capability type has a different trait, so a fully generic registry would require type erasure that loses the API surface.

Auto-discovery: the embedding binary (Tauri or daemon) constructs adapters (passing `SystemContext`) and registers them at startup. No dynamic loading.

## Adapter Locations

| Adapter | Crate | Implements | Dependencies |
|---|---|---|---|
| `ClaudeAdapter` | `nexus-core` | `ChatCapability` | std only (process spawning via `SystemContext`) |
| `OpenCodeAdapter` | `nexus-core` | `ChatCapability` | std only |
| `FsExplorer` | `nexus-core` | `ExplorerCapability` | std::fs |
| `NeovimAdapter` | `nexus-editor` | `EditorCapability` | `nvim-rs` (later) |
| `NullEditor` | `nexus-editor` | `EditorCapability` | none |
| `TmuxMux` | `nexus-tmux` | `Mux` | std (subprocess) |
| `NullMux` | `nexus-core` | `Mux` | none |

Chat adapters live in `nexus-core` because they have no external deps — just process spawning with PATH resolution via `SystemContext`. This mirrors `ClaudeCodeAdapter` in Python which only uses `subprocess` and `shutil.which`.

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
- `chat_send(pane_id, message, cwd)` — gets `registry.best_chat()`, creates channel, calls `send_message(msg, cwd, tx)`, spawns a drain thread that reads from `rx` and publishes to event bus
- `pty_spawn(pane_id, cmd, cwd)` — creates PTY via `PtyManager`, wires output to event bus
- `pty_write(pane_id, data)` — forwards input to PTY
- `pty_resize(pane_id, cols, rows)` — resizes PTY

### Threading contract

The engine is synchronous. Adapters that spawn background work (chat, PTY reader threads) push events through `std::sync::mpsc` channels. The engine provides a drain mechanism: a thread per active stream that reads from the channel and publishes to the `EventBus`. Surfaces subscribe to the bus.

Tauri commands are async but wrap synchronous engine calls. `commands.rs` uses `tauri::async_runtime::spawn_blocking` for engine calls that may block, and subscribes to the event bus to emit Tauri events.

## PTY Management (`nexus-engine/src/pty.rs`)

Moved from `nexus-tauri/src/pty.rs`. The only change: instead of emitting Tauri events directly (`app.emit("pty-output", ...)`), it pushes output through the event bus. The surface subscribes to bus events and forwards them to its rendering layer.

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
    pub id: String,          // "navigate.left"
    pub label: String,       // "Navigate Left"
    pub category: String,    // "Navigation"
    pub binding: Option<String>, // "Alt+h" — populated at merge time from keymap
}
```

Functions:
- `parse_keymap(path) -> Vec<KeyBinding>` — parse `keymap.conf` (same format as Python: `Alt+h = navigate.left`)
- `load_keymap_cascade(global, profile, workspace) -> Vec<KeyBinding>` — merge with last-wins
- `default_keymap() -> Vec<KeyBinding>` — built-in defaults (the Alt+h/j/k/l etc. that are currently hardcoded)
- `default_commands() -> Vec<CommandEntry>` — all known commands with labels
- `merge_bindings(commands, keymap) -> Vec<CommandEntry>` — populates `binding` field on each command from the keymap

For tmux surfaces: `TmuxMux::initialize()` is responsible for calling `tmux bind-key` for each binding in the resolved keymap. The keymap module provides `generate_tmux_bindings(keymap) -> Vec<String>` which outputs `bind-key -n M-h run-shell "nexus-ctl navigate.left"` etc.

Engine exposes:
- `get_keymap() -> Vec<KeyBinding>`
- `get_commands() -> Vec<CommandEntry>` (with bindings populated)

Tauri UI fetches these on init and builds its keyboard handler + command palette dynamically. No more hardcoded switch statements in `App.tsx`.

## Command Dispatch (`nexus-engine/src/dispatch.rs`)

Maps `domain.action` strings to engine operations. Same pattern as Python `dispatch.py`.

```rust
pub fn dispatch(
    core: &mut NexusCore,
    command: &str,
    args: &HashMap<String, Value>,
) -> Result<Value, NexusError> {
    let (domain, action) = command
        .split_once('.')
        .ok_or(NexusError::InvalidState("command must be domain.action".into()))?;
    match domain {
        "navigate" => handle_navigate(core, action, args),
        "pane"     => handle_pane(core, action, args),
        "editor"   => handle_editor(core, action, args),
        "chat"     => handle_chat(core, action, args),
        "stack"    => handle_stack(core, action, args),
        _ => Err(NexusError::NotFound(format!("unknown domain: {domain}"))),
    }
}
```

### Pane actions

`handle_pane` routes to existing `NexusCore` and `Mux` methods:

| Action | Maps to |
|---|---|
| `pane.split` | `core.layout.split_focused()` |
| `pane.close` | `core.layout.close_pane()` |
| `pane.focus` | `core.layout.set_focus()` |
| `pane.zoom` | `core.layout.toggle_zoom()` |
| `pane.resize` | `core.layout.set_ratio()` |
| `pane.swap` | `core.mux.swap_containers()` |
| `pane.send-keys` | `core.mux.send_input()` |

### Navigate actions

| Action | Maps to |
|---|---|
| `navigate.left` | `core.layout.navigate(Nav::Left)` |
| `navigate.right` | `core.layout.navigate(Nav::Right)` |
| `navigate.up` | `core.layout.navigate(Nav::Up)` |
| `navigate.down` | `core.layout.navigate(Nav::Down)` |

### Stack actions

Delegates to existing `core.handle_stack_op()`.

This is the single entry point for all commands — CLI, Tauri IPC, daemon socket protocol, and tmux keybinds all route through here.

## Dependency Graph (After)

```
nexus-core (traits, shared types, simple adapters)
├── ChatCapability, EditorCapability, ExplorerCapability, Mux
├── ClaudeAdapter, OpenCodeAdapter, FsExplorer
├── SystemContext (PATH resolution)
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
7. **Mux is not a Capability.** It is a special case — explicitly chosen at engine construction, not auto-discovered. One active mux per engine.

## Scope

This spec covers porting the capability model only. Not in scope:
- Actual tmux subprocess calls in `TmuxMux` (stays a stub)
- Actual nvim RPC in `NeovimAdapter` (stays a stub)
- Daemon socket protocol implementation (separate spec)
- Tauri embedded socket listener (separate spec)
- Executor and Menu capability types (deferred — no adapters yet)
- Connector/event wiring system (future)
- Boot lists, vault, workspace indexing (future)
