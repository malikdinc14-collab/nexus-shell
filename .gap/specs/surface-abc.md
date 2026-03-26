# Surface ABC — Abstract Surface Contract

> **Status:** Spec — no Rust trait yet. Mux trait exists as a partial implementation.
> **Depends on:** execution-model.md (state ownership), content-provider.md (menu rendering)

---

## 0. Why a Surface ABC

The engine owns all logical state. Surfaces render it. Today the only abstraction is the `Mux` trait (`nexus-core/src/mux.rs`), which models a **multiplexer backend** — it assumes the engine drives an external process (tmux, sway) that physically creates panes. This breaks down for self-rendering surfaces (Tauri, web, Android) where the surface owns its own rendering and the engine just provides state.

A Surface ABC defines what **every** surface must do, regardless of how it renders. The Mux trait becomes an implementation detail of one surface mode, not the surface contract itself.

---

## 1. Surface Modes

Every surface operates in exactly one mode:

| Mode | Engine's Role | Surface's Role | Mux Trait? | Examples |
|------|--------------|----------------|------------|----------|
| **Delegated** | Calls Mux to create/split/destroy physical panes | Translates Mux calls to backend commands | Yes — surface IS the Mux impl | tmux, sway, hyprland, ghostty tabs |
| **Internal** | Maintains layout tree, emits state events | Renders layout tree from events, owns its own draw loop | No — uses NullMux | Tauri, web browser, Android, embedded |
| **Headless** | Maintains state, no rendering | No rendering — used for tests, daemon-only, scripting | No — uses NullMux | CLI client, test harness, daemon without display |

**Rule:** A surface declares its mode at registration time. The engine adapts its behavior accordingly:
- Delegated: engine calls `mux.split()`, `mux.focus()`, etc. after state mutations.
- Internal: engine emits state-change events. Surface renders from events.
- Headless: engine mutates state. Events still publish to the bus (subscribers may exist), but no rendering occurs.

---

## 2. The Surface Trait

The `Surface` trait is a **wire-protocol contract** — not an in-process Rust trait. Surfaces are separate binaries (Tauri app, tmux launcher, web server) that connect over Unix socket. The Rust trait below defines the contract for documentation; the canonical form is the JSON-RPC protocol in Section 4.

```rust
/// What every surface must declare. This is NOT the Mux trait.
/// The Mux trait is one possible implementation detail for Delegated surfaces.
///
/// NOTE: This trait is primarily documentary. Internal and Headless surfaces
/// implement the contract via JSON-RPC over the wire, not in-process.
/// Only Delegated surfaces may implement this in-process (same binary as daemon).
pub trait Surface: Send + Sync {
    /// Unique identifier for this surface instance.
    fn id(&self) -> &str;

    /// Human-readable name (e.g. "Tauri Desktop", "tmux", "Web").
    fn name(&self) -> &str;

    /// Which rendering mode this surface operates in.
    fn mode(&self) -> SurfaceMode;

    /// Declare what this surface can do.
    fn capabilities(&self) -> SurfaceCapabilities;

    /// Called once when the surface connects to the engine.
    /// Returns the initial state the surface needs to render.
    fn on_connect(&mut self, state: &EngineSnapshot) -> Result<(), SurfaceError>;

    /// Called when the surface disconnects (clean shutdown or crash).
    fn on_disconnect(&mut self);
}

pub enum SurfaceMode {
    /// Engine drives physical layout via Mux trait.
    Delegated,
    /// Surface renders from engine state events.
    Internal,
    /// No rendering. State access only.
    Headless,
}
```

**For Delegated surfaces**, the implementation also provides a `Mux`, giving the engine direct control over the backend. The engine holds these as separate fields — not a composite trait object:

```rust
// In NexusCore:
pub mux: Box<dyn Mux>,                          // drives physical panes (existing)
pub surfaces: Vec<SurfaceRegistration>,          // tracks connected surfaces (new)

// SurfaceRegistration is a data struct, not a trait object:
pub struct SurfaceRegistration {
    pub id: String,
    pub name: String,
    pub mode: SurfaceMode,
    pub capabilities: SurfaceCapabilities,
}
```

The `mux` field remains as-is. `surfaces` is a registry of who's connected and what they support. For Delegated surfaces, the `mux` field IS the surface's Mux impl (set at daemon startup). For Internal/Headless surfaces, they're socket clients tracked in `surfaces` but never touch `mux`.

---

## 3. Surface Capabilities

Surfaces declare what they support. The engine (and menu system) adapts accordingly.

```rust
pub struct SurfaceCapabilities {
    // -- Rendering --
    pub popup: bool,          // Can show floating overlays (tmux display-popup, Tauri dialog)
    pub menu: bool,           // Can render menu/command palette (fzf, gum, cmdk)
    pub hud: bool,            // Can show persistent status bar (tmux status-line, Tauri bar)
    pub notifications: bool,  // Can show toasts/alerts (tmux display-message, OS notification)
    pub rich_content: bool,   // Can render HTML/markdown/images (Tauri webview, web, NOT tmux)

    // -- Layout --
    pub internal_tiling: bool,  // Surface does its own tiling (Tauri, web)
    pub external_tiling: bool,  // Surface delegates tiling to backend (tmux, sway)
    pub detachable_panes: bool, // Panes can become OS windows (Tauri, sway)
    pub transparency: bool,     // Surface supports transparent backgrounds (Tauri, compositor)
    pub gaps: bool,             // Surface supports gaps between panes (Tauri desktop mode)
    pub multi_window: bool,     // Surface supports multiple OS windows / monitors

    // -- Input --
    pub keyboard: bool,       // Can receive keyboard events
    pub mouse: bool,          // Can receive mouse/touch events
    pub touch: bool,          // Touchscreen (Android, iPad)

    // -- Lifecycle --
    pub persistent: bool,     // Survives client disconnect (tmux, daemon mode)
    pub multi_client: bool,   // Multiple clients can attach simultaneously
    pub reconnectable: bool,  // Supports reconnect with state reconciliation
}
```

**Capability discovery is bidirectional:**
- Engine queries surface capabilities to decide what UI features to offer.
- Menu system filters actions by surface capabilities (e.g., "Detach Pane" only appears if `detachable_panes == true`).
- Content providers check capabilities to decide what to render (rich markdown vs plain text).

**Capability honesty:** If a surface declares a capability it cannot fulfill, the failure is treated like any adapter failure — the engine logs it and degrades. No crash, no retry loop. Capabilities are trust-based; the surface is responsible for accuracy.

---

## 4. Connection Protocol

All surfaces connect to the engine through the daemon. The protocol is the same regardless of mode.

```
Surface                          Daemon                          Engine
  │                                │                                │
  ├── connect(socket) ────────────►│                                │
  │                                ├── register_surface(id, caps) ──►│
  │◄── EngineSnapshot ────────────┤◄── initial_state ──────────────┤
  │                                │                                │
  │── subscribe(["*.*"]) ────────►│                                │
  │◄── event stream ──────────────┤◄── EventBus notifications ────┤
  │                                │                                │
  │── request("domain.action") ──►│── dispatch(command, args) ────►│
  │◄── JSON result ───────────────┤◄── Result<Value> ──────────────┤
  │                                │                                │
  │── disconnect ─────────────────►│── unregister_surface(id) ─────►│
```

### 4.1 Initial Handshake

On connect, the surface sends a `surface.register` request. **This is a new dispatch domain — does not exist yet.**

```json
{
  "method": "surface.register",
  "params": {
    "id": "tauri-main",
    "name": "Tauri Desktop",
    "mode": "internal",
    "capabilities": {
      "popup": true,
      "menu": true,
      "rich_content": true,
      "internal_tiling": true,
      "detachable_panes": true,
      "transparency": true,
      "gaps": true,
      "multi_window": true,
      "keyboard": true,
      "mouse": true
    }
  }
}
```

The engine responds with an `EngineSnapshot` — enough state to fully render:

```json
{
  "layout": { "root": {...}, "focused": "pane-1", "zoomed": null },
  "session": "my-project",
  "cwd": "/home/user/project",
  "keymap": [...],
  "commands": [...],
  "capabilities": [...]
}
```

**Backwards compatibility:** Until `surface.register` is implemented, surfaces can skip registration and just use `layout.show`, `keymap.get`, `commands.list` etc. individually (the current Tauri pattern). Registration is an optimization, not a gate.

### 4.2 Event Subscription

After registration, the surface subscribes to events. The daemon bridges `EventBus` notifications to the socket.

**Event name mapping** — The `EventBus` uses `EventType` enum variants internally. The daemon's event bridge translates to dotted wire names:

| EventType (Rust enum) | Wire name (JSON-RPC) | Tauri bridge name | Who subscribes |
|----------------------|----------------------|-------------------|---------------|
| `Custom("layout.changed")` | `layout.changed` | `layout-changed` | All rendering surfaces |
| `Custom("session.changed")` | `session.changed` | `session-changed` | All rendering surfaces |
| `Custom("pty.output")` | `pty.output` | `pty-output` | Surfaces with terminals |
| `Custom("pty.exit")` | `pty.exit` | `pty-exit` | Surfaces with terminals |
| `Custom("agent.start/text/done")` | `agent.*` | `agent-output` | Surfaces with chat |
| `StackPush/StackPop` | `stack.changed` | `stack-changed` | Surfaces with tab UI |
| `Custom("editor.file_opened")` | `editor.file_opened` | `editor-file-opened` | Surfaces with editor |

> **Note:** Most events today use `EventType::Custom` with a source string. The typed variants (`StackPush`, `PaneSplit`, etc.) exist in the enum but the daemon's event bridge maps them to the dotted wire format. The wire protocol uses dotted names exclusively.

**Required events** (all rendering surfaces must handle):
- `layout.changed` — layout tree updated
- `session.changed` — workspace/session switched *(not yet emitted — needs implementation)*

**Optional events** (surface subscribes based on what it renders):
- `pty.output` / `pty.exit` — terminal data
- `agent.*` — chat streaming
- `stack.changed` — tab stack mutations
- `editor.file_opened` — cross-pane file open

### 4.3 Command Dispatch

Surfaces send commands via JSON-RPC:

```json
{ "method": "navigate.left", "params": {} }
{ "method": "pane.split", "params": { "direction": "vertical", "pane_type": "terminal" } }
{ "method": "editor.open", "params": { "path": "/tmp/foo.rs", "name": "foo.rs" } }
```

The dispatch domains are the universal command vocabulary. No surface-specific commands exist — if a surface needs something, it becomes a new domain/action in dispatch. Current domains: `navigate`, `pane`, `stack`, `chat`, `pty`, `session`, `keymap`, `commands`, `layout`, `capabilities`, `nexus`, `fs`, `editor`. The `surface` domain will be added as part of Phase A.

---

## 5. PTY Ownership by Mode

PTY (pseudo-terminal) ownership differs by surface mode. This is critical — two things can own a shell process, and they must not conflict.

| Mode | Who owns PTY processes | `pty.*` dispatch behavior |
|------|----------------------|--------------------------|
| **Delegated** | The backend (tmux owns shells in its panes) | `pty.spawn` → forwarded to `mux.attach_process()`. Engine's `PtyManager` is **not used**. |
| **Internal** | Engine's `PtyManager` (spawns real PTY via `portable-pty`) | `pty.spawn` → `PtyManager::spawn()`. Surface receives `pty.output` events. |
| **Headless** | Engine's `PtyManager` (if explicitly spawned) | Same as Internal, but no surface renders the output. |

**Rule:** The dispatch handler for `pty.*` must check the active surface mode. If Delegated, it delegates to the Mux. If Internal/Headless, it uses `PtyManager`.

**Current state:** `PtyManager` always handles PTY. This works because only Internal surfaces (Tauri) exist today. When TmuxMux ships, `handle_pty()` in dispatch must become mode-aware.

---

## 6. Surface Multiplicity

Multiple surfaces can connect simultaneously. The rules:

| Scenario | Allowed? | How it works |
|----------|----------|-------------|
| 1 Delegated + N Internal | Yes | Delegated surface is the `mux`. Internal surfaces render from events. Both see same state. |
| N Internal (no Delegated) | Yes | All render from events. Default `NullMux`. This is the current Tauri + CLI setup. |
| 2+ Delegated | **No** | Only one Mux can drive physical panes. Second Delegated surface is rejected at registration. |
| 0 surfaces | Yes | Daemon runs headless with NullMux. CLI can still send commands. |

**Layout sharing:** All surfaces share one layout tree. There is no per-surface layout. If tmux (Delegated) and Tauri (Internal) are both connected, they see and render the same pane arrangement. This is intentional — the engine is the single source of truth.

**Multi-monitor / multi-window:** Handled within a single surface instance. A Tauri surface with `multi_window: true` manages its own window placement across monitors. The engine doesn't know about monitors — it knows about panes. Detachable panes (`detachable_panes: true`) are the mechanism for spreading panes across windows/monitors.

---

## 7. Surface Spectrum

Concrete surfaces ordered by rendering complexity:

### 7.1 Headless / CLI

```
Mode: Headless
Capabilities: { keyboard: true }
Connection: NexusClient, one-shot request/response
Mux: NullMux (or none)
```

The `nexus` CLI binary. Each invocation connects, sends one command, prints result, disconnects. No persistent rendering. Already exists in `nexus-cli`.

### 7.2 tmux (Delegated)

```
Mode: Delegated
Capabilities: { popup, menu, hud, notifications, external_tiling, keyboard, persistent, multi_client, reconnectable }
Connection: Daemon spawns with TmuxMux as the active Mux
Mux: TmuxMux (calls tmux CLI via std::process::Command)
```

The engine calls `TmuxMux` methods which translate to `tmux split-window`, `tmux send-keys`, etc. Keybindings are tmux key-tables that invoke `nexus dispatch <command>`. The tmux status bar is driven by `show_hud()`.

**Stub exists** at `nexus-tmux/src/lib.rs`. Needs real implementation.

**Async concern:** Mux trait methods are synchronous. `TmuxMux` shells out to `tmux` which blocks. Since `NexusCore` is behind `Arc<Mutex>`, every Mux call holds the global lock during subprocess execution. Mitigation options:

| Option | Tradeoff |
|--------|----------|
| `spawn_blocking` in daemon | Requires daemon to be async-aware around dispatch. Mux trait stays sync. |
| Make Mux trait async | Breaks NullMux simplicity. Every impl needs async runtime. |
| Accept the blocking | tmux calls are fast (<10ms). Lock contention is low with few clients. Start here. |

**Recommendation:** Start with synchronous blocking. Measure. Migrate to `spawn_blocking` only if lock contention becomes observable.

### 7.3 OS Window Manager (Delegated)

```
Mode: Delegated
Capabilities: { external_tiling, detachable_panes, multi_window, keyboard, persistent, reconnectable }
Connection: Daemon spawns with SwayMux / HyprlandMux
Mux: SwayMux (calls sway-msg) / HyprlandMux (calls hyprctl)
```

Same pattern as tmux but targeting tiling WMs. Each pane is an OS window. The engine tells the WM where to place them. Deferred — no code exists.

### 7.4 Terminal Multiplexer (Delegated)

```
Mode: Delegated
Capabilities: { external_tiling, keyboard, persistent }
Connection: Daemon spawns with GhosttyMux / KittyMux
Mux: GhosttyMux / KittyMux (terminal-specific IPC)
```

For terminals with split/tab APIs (Ghostty, Kitty, WezTerm). Deferred.

### 7.5 Tauri Desktop (Internal)

```
Mode: Internal
Capabilities: { popup, menu, hud, notifications, rich_content, internal_tiling, detachable_panes, transparency, gaps, multi_window, keyboard, mouse }
Connection: NexusClient (via Tauri IPC bridge) + event subscription
Mux: NullMux (engine doesn't drive rendering)
```

The React frontend renders the layout tree from `layout.changed` events. Panes are React components. Tiling, gaps, transparency are CSS. Detachable panes become Tauri `WebviewWindow` instances.

**Already implemented** (the 7 modularity fixes ensure this is clean).

### 7.6 Web Browser (Internal)

```
Mode: Internal
Capabilities: { popup, menu, notifications, rich_content, internal_tiling, multi_window, keyboard, mouse, reconnectable }
Connection: WebSocket to daemon + event subscription
Mux: NullMux
```

Same React/TypeScript frontend as Tauri, but served over HTTP. Connection via WebSocket instead of Tauri IPC. Needs reconnection protocol (full state snapshot on reconnect). Phase 5.

### 7.7 Android / Mobile (Internal)

```
Mode: Internal
Capabilities: { notifications, rich_content, internal_tiling, keyboard, mouse, touch }
Connection: NexusClient (via JNI/FFI bridge or WebSocket)
Mux: NullMux
```

Likely shares web frontend code or uses native views. Touch input. Single-pane default with swipe to switch. Deferred.

---

## 8. Delegated Surface: Engine ↔ Mux Flow

For delegated surfaces, the engine drives the surface through the Mux trait. The flow on a `pane.split` command:

```
User presses Alt+v
  → tmux keybind runs: nexus dispatch pane.split --direction vertical
    → CLI sends JSON-RPC to daemon
      → dispatch("pane.split", {direction: "vertical"})
        → core.layout.split_focused(Vertical, Terminal)   // logical state
        → core.mux.split(handle, Vertical, 0.5, cwd)     // physical state via Mux
          → TmuxMux runs: tmux split-window -v -p 50 -c /path
        → emit layout.changed event
      → return layout JSON
    → CLI prints result (or silent)
```

**Key:** The engine mutates logical state first, then instructs the Mux to create the physical pane.

> **Note — rollback is not yet implemented.** If the Mux call fails after logical state is mutated, the engine currently has no rollback mechanism. This is a known gap. For Phase B, Mux failures should log an error and the engine should attempt to undo the logical mutation. Full transactional rollback is deferred.

---

## 9. Internal Surface: Engine ↔ Event Flow

For internal surfaces, the engine emits events and the surface renders from them:

```
User presses Alt+v (in Tauri)
  → React keydown handler matches binding
    → dispatchCommand("pane.split", {direction: "vertical"})
      → Tauri IPC → NexusClient → daemon → dispatch()
        → core.layout.split_focused(Vertical, Terminal)   // logical state
        → emit layout.changed event                        // no Mux call
      → return layout JSON
    → React updates layout state from response
  → (simultaneously) layout.changed event arrives via event bridge
    → React updates layout state from event (idempotent)
```

**Key:** Internal surfaces get state from both the command response AND the event stream. Both paths lead to the same state. The event stream also delivers changes from other clients.

---

## 10. Hot-Swap: Switching Surfaces

A user might start in tmux, then launch Tauri, or vice versa. The hot-swap protocol:

**tmux → Tauri (add Internal to existing Delegated):**
1. Tauri connects, registers as Internal surface.
2. Receives `EngineSnapshot` — renders the same layout tmux is showing.
3. Both surfaces are active simultaneously (Section 6 allows 1 Delegated + N Internal).
4. User can close tmux. Delegated surface unregisters. Engine continues with NullMux. Tauri keeps rendering.

**Tauri → tmux (add Delegated to existing Internal):**
1. Daemon restarts with TmuxMux instead of NullMux (requires daemon restart — hot-swap of Mux impl is deferred).
2. TmuxMux creates tmux session, engine replays current layout tree via Mux calls.
3. Tauri remains connected as Internal surface.

**PTY migration on surface switch:**
- PTYs spawned by `PtyManager` (Internal mode) cannot be migrated to tmux ownership. They remain engine-owned.
- PTYs spawned by tmux (Delegated mode) cannot be migrated to `PtyManager`.
- On surface mode change, existing PTYs are killed and respawned in the new owner. This is disruptive but correct — session persistence (save/restore) mitigates data loss.

---

## 11. State Reconciliation (Phase 5 Target)

Currently state flows one way: engine → surface. For delegated surfaces (tmux), users can manually split panes, resize, etc. outside the engine's knowledge. The reconciliation protocol:

1. Surface reports physical state: `surface.report_state` → `{ panes: [...], geometry: {...} }`
2. Engine diffs against logical state
3. Engine either adopts the change (user split a pane → register it) or corrects the surface (rogue pane → destroy it)
4. Reconciliation runs on: reconnect, periodic heartbeat, explicit `surface.sync` command

**Not implemented.** Current workaround: engine is single source of truth. Manual tmux operations outside nexus are invisible to the engine.

---

## 12. Implementation Checklist

### Phase A: Surface Trait (Rust)
- [ ] Define `SurfaceMode`, `SurfaceCapabilities`, `SurfaceRegistration` in `nexus-core`
- [ ] Add `surfaces: Vec<SurfaceRegistration>` to `NexusCore`
- [ ] Add `surface` dispatch domain: `register`, `unregister`, `list`, `capabilities`
- [ ] Daemon tracks registered surfaces
- [ ] Engine queries surface capabilities before emitting render-specific events
- [ ] Make `handle_pty()` mode-aware (check if Delegated surface is active)

### Phase B: tmux Surface (First Delegated)
- [ ] Implement `TmuxMux` methods with real `tmux` CLI calls (synchronous `std::process::Command`)
- [ ] tmux key-table config that routes Alt+* to `nexus dispatch <command>`
- [ ] HUD rendering via `tmux set status-left/right`
- [ ] Menu via `tmux display-menu` or `fzf-tmux`
- [ ] Popup via `tmux display-popup`
- [ ] Daemon launch flag: `--mux tmux` (vs default `--mux null`)

### Phase C: Tauri Surface (Refactor to Surface Trait)
- [ ] Send `surface.register` on app startup
- [ ] Capability-aware command palette (filter by surface capabilities)
- [ ] Replace init waterfall with single `EngineSnapshot` from registration response

### Phase D: Web Surface
- [ ] WebSocket transport for NexusClient
- [ ] Reconnection with full state snapshot
- [ ] Same React frontend, different transport

### Phase E: Reconciliation
- [ ] `surface.report_state` protocol
- [ ] Diff algorithm for layout tree
- [ ] Adopt-or-correct policy engine

---

## 13. Relationship to Existing Code

| Existing | Role in Surface ABC |
|----------|-------------------|
| `Mux` trait (`nexus-core/src/mux.rs`) | Implementation detail of Delegated surfaces. Unchanged. |
| `NullMux` | Default Mux for Internal and Headless surfaces. Unchanged. |
| `TmuxMux` stub (`nexus-tmux/src/lib.rs`) | Will implement real tmux calls. No Surface trait needed — registration is over the wire. |
| `NexusClient` (`nexus-client/src/client.rs`) | Wire protocol for all surfaces. Add `surface.register` convenience method. |
| `EventSubscription` (`nexus-client/src/events.rs`) | Event delivery for all surfaces. Unchanged. |
| `dispatch()` (`nexus-engine/src/dispatch.rs`) | Universal command vocabulary. Add `surface` domain. |
| `NexusCore.mux` field | Stays as `Box<dyn Mux>`. Add `surfaces: Vec<SurfaceRegistration>` alongside it. |
| Tauri event bridge (`nexus-tauri/src/main.rs`) | Internal surface pattern. Add registration call. |
