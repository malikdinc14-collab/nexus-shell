# Spec: Execution Model

> Defines the runtime semantics of Nexus Shell — what happens when, in what order, with what guarantees.

---

## 1. State Ownership

### The Rule

> **Engine owns the plan. Surface owns the ground truth. They reconcile.**

The engine is NOT the single source of truth for everything. State ownership is split:

| Component | Owns (authoritative) | Does NOT own |
|-----------|---------------------|--------------|
| **NexusCore** (engine) | Logical state: stacks, tabs, config, pack enablement, event history, dispatch routing | Physical state: geometry, focus, process liveness |
| **Surface** (via `Mux` trait — tmux/web/Tauri) | Physical state: actual geometry, process liveness, focus, user-initiated changes | Logical state: what stacks exist, what tabs are in them, config |
| **Adapters** | Tool-specific protocol state (RPC sockets, CLI flags, ephemeral tool state) | State beyond their tool's scope |
| **Content providers** | Their own output for a single invocation | Anything. They are stateless functions. |
| **Live sources** | Nothing — they query and return | Cached state, subscriptions |

### Conflict Resolution

When engine and surface disagree:

| Conflict type | Who wins | Example |
|--------------|----------|---------|
| Logical state (stacks, tabs, config) | Engine | Engine says 2 tabs, surface shows 3 → surface re-syncs |
| Physical state (geometry, focus, process state) | Surface | Surface reports pane resized → engine updates its model |
| Unknown state (surface has things engine doesn't know about) | Reconcile | User split a pane manually → engine discovers and registers it |

**The mental model:** like a deployment system. Desired state lives in the spec (engine). Actual state lives on the machines (surface). A reconciliation loop keeps them aligned. Neither is absolute.

**Rust implementation reference:** `NexusCore` (in `crates/nexus-engine/src/core.rs`) holds `StackManager` (tab state), `EventBus` (event history, in `bus.rs`), `CapabilityRegistry` (adapter selection, in `registry.rs`), `LayoutTree` (logical layout), `PtyManager` (process ownership). Surfaces implement the `Mux` trait (in `crates/nexus-core/src/mux.rs`) and expose `get_focused()`, `list_panes()`, etc.

> **Note — reconciliation is aspirational.** The current Rust codebase has no bidirectional state sync. State flows outward only: `NexusCore` → `Mux` → surface. Surfaces are output backends; they do not push physical state changes back to the engine. The reconciliation model described above is the target architecture for Phase 5 (web surface). Until then, the engine is effectively the single source of truth.

### State Mutation Rules

1. Only the engine mutates logical workspace state (stacks, config, pack enablement).
2. Surfaces report user actions (keypresses, menu selections) as **intents**, not mutations.
3. The engine processes intents, mutates state, then instructs the surface to update.
4. Surfaces report physical changes (resize, focus, process exit) as **events** that the engine incorporates.
5. Adapters may hold ephemeral tool state (nvim buffer list, process PIDs) — this is tool-internal, not workspace state.
6. On reconnect/attach, the engine reconciles its logical state against the surface's physical state.

---

## 2. Workspace Lifecycle

A workspace progresses through a defined lifecycle. Events are emitted at each transition.

```
BOOT → RUNNING → DETACH → (ATTACH → RUNNING)
          ↓                        ↓
        SHUTDOWN               SHUTDOWN
```

Note: SAVING is not a lifecycle state — it's a synchronous operation that occurs within RUNNING (explicit save) or during DETACH (auto-save). It does not block state transitions.

### Phases

**BOOT** — Surface and engine initialize.
- Surface creates session/window structure
- Engine loads config cascade, discovers project, detects packs
- Boot list executes (ordered, with `wait_for` barriers)
- Events: `boot.start`, `boot.progress`, `boot.item.ok`/`boot.item.fail`, `boot.complete`

**ATTACH** — Client connects to an existing session.
- Surface attaches to existing session
- Engine re-syncs state (stacks, config)
- Layout restored from momentum snapshot
- Event: `workspace.restore`

**RUNNING** — Normal operation.
- User actions → engine intents → state mutations → surface updates
- Content providers run on demand (menu open)
- Live sources query on demand or on timer
- Connectors fire on matching events
- **Save** is a synchronous operation within RUNNING (explicit `workspace save` or auto-save before detach). Engine serializes stacks + geometry to disk, emits `workspace.save` event, then returns to RUNNING.

**DETACH** — Client disconnects.
- Auto-save triggered (synchronous, within DETACH)
- Surface releases client
- Engine lifecycle decision:
  - **Daemon mode** (default for tmux): engine persists, session stays alive, clients can re-attach
  - **Single-client mode** (web surface default): engine shuts down after last client disconnects + grace period (30s)
  - Controlled by `config.engine.persistence`: `daemon` | `single-client`

**SHUTDOWN** — Everything stops.
- Boot list shutdown hooks execute (reverse order)
- Event: `boot.shutdown`
- Processes terminated, socket closed

### Boot List Execution Model

Boot items execute **sequentially** by default. Each item:

1. Resolves `role` to a target pane via engine state
2. Dispatches command through adapter (`mux.send_command()` for terminal, `editor.open_resource()` for editor)
3. If `wait_for` is set: polls pane output for pattern match, with timeout
4. If item fails: logs failure, continues (unless `required: true`)
5. Events emitted per item: `boot.item.ok` or `boot.item.fail`

**Rust implementation reference:** `EventType` in `crates/nexus-engine/src/bus.rs` defines `BootStart`, `BootComplete`, `BootItemOk`, `BootItemFail`. Boot list execution (the `BootRunner`) has not been ported to Rust yet — it remains in legacy Python at `core/engine/project/boot.py`. Shutdown hooks are also unimplemented in Rust.

---

## 3. Event Ordering & Delivery

### Bus Semantics

The event bus (`EventBus` in `crates/nexus-engine/src/bus.rs`) provides:

- **Synchronous inline delivery** — subscribers are called inline; the publisher blocks until all subscribers complete. This is the current Rust implementation.
- **Async event bridge (daemon)** — `crates/nexus-daemon/src/event_bridge.rs` decouples the sync `EventBus` from async socket writes via `tokio::sync::mpsc::unbounded_channel`. This is the existing mechanism for streaming events to connected clients (JSON-RPC notifications over Unix socket).
- **Future: full async delivery** — for web surface (WebSocket), long-running connectors. Under async delivery, publishers do NOT wait. This is the target for Phase 5.
- **In-order within a single publisher** — events from one source arrive in emit order. Events are stored in a `VecDeque` (FIFO). Note: callback dispatch iterates a `HashMap` of subscribers, so delivery order across subscribers is not guaranteed.
- **No cross-publisher ordering** — events from different sources may interleave
- **At-most-once delivery** — no replay, no acknowledgment, no retry
- **Wildcard subscription** — `stack.*` matches `stack.push`, `stack.pop`, etc.
- **Dead subscriber detection** — subscribers that fail 3 consecutive times (configurable `dead_threshold`) are marked dead and skipped on future events. This is more tolerant than "raise = remove."

**Note:** "Fire-and-forget" describes the semantic contract (publishers should not depend on subscriber behavior), even though the current implementation is synchronous. Subscribers must not assume they can block the publisher indefinitely — they should complete quickly or delegate to a background task.

### What This Means

The bus is suitable for:
- UI updates (HUD refresh, tab bar redraw)
- Connector triggers (save → run tests)
- Logging and telemetry

The bus is NOT suitable for:
- Transactional coordination (use direct function calls)
- Guaranteed delivery (use explicit confirmation)
- Ordered cross-component workflows (use the boot sequence model)

### Sync vs Async Events

Currently all events are synchronous (subscribers called inline). Future phases may introduce async delivery for:
- Web surface (events sent over WebSocket)
- Long-running connector actions
- Cross-process event bridging

When full async delivery is added, the contract must specify:
- **Sync events**: subscriber completes before publisher continues
- **Async events**: subscriber notified eventually, no ordering guarantee cross-publisher

> **Note on `EventType` vs `source` field:** Events carry both an `EventType` enum variant and a `source` string (e.g., `"stack.push"`). Pattern matching in subscriptions runs against `event.source`, not `event.event_type`. These two fields can diverge — the `source` string is the canonical subscription target.

---

## 4. Provider Execution Lifecycle

> See `content-provider.md` for the full contract. This section covers execution timing only.

### When Providers Run

| Trigger | What Runs | Caching |
|---------|-----------|---------|
| Menu opens (Alt+m) | All content providers for the active context | None by default (CachedProvider wrapper available for expensive queries) |
| Context navigation (drill into submenu) | Providers for the new context only | None by default |
| Live source refresh | Python resolvers on timer | TTL-based (per resolver config) |
| Boot sequence | Boot list items, sequentially | N/A |

### Result Merging

When multiple layers provide content for the same context (e.g., `build/`):

1. **Layer order**: system → builtin → user → profile → workspace
2. **Static YAML** (`_list.yaml`): last layer wins for metadata (name, icon, layout)
3. **Dynamic scripts** (`list.sh`): all layers run, results concatenated
4. **Shadow exclusions** (`_shadow`): any layer can hide items by name
5. **Policy** (from `lists.yaml`): `override` replaces; `aggregate` concatenates

**Legacy Python reference:** `menu_engine.py` `get_list_layers()` and `load_metadata()` implement this cascade.

> **Rust status:** Content providers, the menu engine, and the layered discovery system do not exist in the Rust crates. The Rust engine uses `dispatch.rs` (domain.action routing across 11 domains) instead of the Python command graph. When content providers are ported, they will integrate with the dispatch system rather than reimplementing the command graph. See `content-provider.md` for the target Rust trait design.

### Timeout & Failure

- Content providers: 5 second timeout (kill if exceeded)
- On timeout: provider output discarded, menu renders without it, warning logged
- On invalid output (not JSON): line skipped, warning logged
- On provider crash (non-zero exit): treated as empty output, warning logged
- Menu always renders — provider failures degrade content, never block UI

---

## 5. Connector Execution Model

Connectors wire events to actions. They are the automation layer.

### Semantics

1. Connector trigger matches against event type (exact or wildcard)
2. On match: action executes **asynchronously** (background, non-blocking)
3. Actions are either:
   - `shell:` — command dispatched through adapter
   - `internal:` — engine function call (e.g., `editor.goto`)
4. **Loop prevention:** Connector cascades have a max depth of **3**. If connector A's action triggers an event that matches connector B, which triggers an event matching connector C — that's depth 3 and allowed. Depth 4 is blocked and logged as a warning. Additionally, the same connector cannot fire twice within a single cascade (dedup by connector ID).
5. Connectors have no return value — they are fire-and-forget

### Failure

- Shell action fails → logged, no retry
- Internal action fails → logged, no retry
- Connector itself fails → removed from active set, warning emitted

---

## 6. Surface Update Protocol

When engine state changes, the surface must reflect it. The protocol:

1. Engine mutates state (push tab, switch composition, etc.)
2. Engine calls surface method(s) to update display
3. Surface applies changes to its rendering layer
4. Surface confirms (return value or no exception)

**For logical state**, the engine instructs the surface. **For physical state**, the engine queries the surface. The surface is authoritative for geometry, focus, and process liveness — the engine reads these via `Mux` trait methods (`get_focused()`, `list_panes()`, etc. in `crates/nexus-core/src/mux.rs`).

### Future: WebSocket Update Protocol

For the web surface, step 2 becomes:
1. Engine serializes state delta as JSON message
2. WebSocket server sends to connected clients
3. Browser applies delta to DOM
4. No confirmation needed (optimistic rendering)

Reconnection: client receives full state snapshot on connect, then deltas thereafter.

---

## 7. Failure Philosophy

### The Rules

1. **Provider failures are silent to the user** — degrade content, never block UI
2. **Adapter failures are visible** — display error in pane, log with context
3. **Engine failures are loud** — log with full traceback, emit error event
4. **Surface failures are recoverable** — reconcile logical state (engine) with physical state (surface)
5. **Boot failures are per-item** — log and continue unless `required: true`
6. **No silent swallowing** — every catch block logs. Empty `except: pass` is a bug.

### Crash Recovery

The engine does not implement WAL, journaling, or crash-safe atomicity. Recovery semantics are:

1. **Last auto-save wins.** The daemon auto-saves every 30 seconds when the `dirty` flag is set. On crash, the most recent `state.json` in `~/.nexus/sessions/<name>/` is the recovery point. Up to 30 seconds of state may be lost.
2. **Snapshots are durable.** Explicit snapshots (`session.save`) are written synchronously to disk and survive crashes.
3. **Layout is recoverable.** If `state.json` exists on daemon startup, layout and stacks are restored from it.
4. **PTY processes are not recovered.** Terminal processes (spawned via `PtyManager`) are lost on crash. Restoration creates new panes but does not re-spawn processes. Boot lists are the mechanism for re-establishing running state.
5. **No partial write protection.** `save_workspace` writes the full JSON atomically via `std::fs::write`, but a crash during write could leave a truncated file. Future: write to `.tmp` then `rename()` for atomic replacement.

### Current Gaps (Honest)

- Provider timeout is not implemented in Rust — providers can hang indefinitely (Python legacy also lacks this)
- No reconnection protocol exists yet (needed for web surface, Phase 5)
- No atomic file writes — crash during save could corrupt `state.json` (see crash recovery point 5)
- `NexusError` has 5 variants (`NotFound`, `InvalidState`, `Io`, `Protocol`, `Other` in `crates/nexus-core/src/error.rs`) but no `Error` event type exists in `EventType` for broadcasting failures
- Adapter failures are silent — `CapabilityRegistry` falls back to `.best_*()` but does not emit error events
