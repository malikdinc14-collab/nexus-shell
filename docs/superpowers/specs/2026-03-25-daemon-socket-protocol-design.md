# Daemon Socket Protocol — Design Spec

> Unlock tmux, CLI, and pane-as-OS-window surfaces by making the engine a standalone daemon that all surfaces connect to over Unix domain sockets using JSON-RPC 2.0.

## Context

The capability model port moved all tool logic into the engine. But Tauri still embeds `NexusCore` in-process — other surfaces (CLI, tmux, future OS-window panes) can't reach it. The daemon socket protocol makes the engine a shared service that all surfaces connect to as equal peers.

**Supersedes capability model spec deployment model.** The capability model spec described "Approach C" where Tauri embeds the engine in-process AND exposes a socket. This spec replaces that with a cleaner architecture: the engine lives exclusively in `nexus-daemon`, and Tauri becomes a pure client. This eliminates the two-mode complexity (embedded vs. standalone) in favor of a single deployment model.

## Architecture

```
nexus-daemon (always-on process)
    ├── NexusCore (engine, registry, PTY, event bus)
    ├── Command listener (unix socket, JSON-RPC 2.0)
    └── Event listener (unix socket, filtered subscriptions)

Clients (all equal peers):
    ├── nexus-tauri (GUI windows)
    ├── nexus-cli (one-shot commands)
    ├── nexus-tmux (mux adapter, calls back via socket)
    └── future: pane-as-OS-window processes
```

### Key invariant

**Tauri no longer embeds the engine.** It becomes a pure client like everything else. `NexusCore` lives exclusively in `nexus-daemon`. All surfaces are equal peers.

### Socket paths

- Command: `$XDG_RUNTIME_DIR/nexus/nexus.sock` (existing `constants::socket_path()`)
- Events: `$XDG_RUNTIME_DIR/nexus/nexus-events.sock`

Fallback (no `XDG_RUNTIME_DIR`): `/tmp/nexus-<uid>/nexus.sock` and `/tmp/nexus-<uid>/nexus-events.sock`.

### Auto-launch

Client library tries to connect to the command socket. If no socket exists:

1. Locate `nexus-daemon` binary: check `NEXUS_DAEMON_BIN` env var first, then look in the same directory as the client binary (`current_exe().parent()`), then fall back to PATH
2. Spawn as a detached background process
3. Poll for socket existence (50ms intervals, up to 3s)
4. Connect once socket appears
5. If socket never appears → `NexusError::Protocol("daemon failed to start")`

### Idle shutdown

Daemon shuts down after 30 seconds with no connected clients AND no active PTYs. Shutdown sequence: (1) stop accepting new connections, (2) re-check idle conditions, (3) if still idle proceed with cleanup. A PID file at `$XDG_RUNTIME_DIR/nexus/nexus.pid` (or `/tmp/nexus-<uid>/nexus.pid`) tracks the daemon process.

## Wire Protocol

**JSON-RPC 2.0** over Unix domain sockets, newline-delimited (NDJSON). One JSON object per line, `\n` terminated.

### Two-connection model

Each client opens up to two connections:

1. **Command connection** (`nexus.sock`) — request/response. Client sends one request, waits for the response, then sends the next. The `id` field enables future multiplexing if needed, but the sync client is serial.

2. **Event connection** (`nexus-events.sock`) — server-push only. Client sends a `subscribe` request, receives acknowledgment, then receives a filtered stream of notifications. The event connection is optional — one-shot CLI commands don't need it. Multiple `subscribe` requests can be sent to replace the active subscription (e.g., to watch a new pane).

**Why two connections:** Backpressure isolation. A pane dumping megabytes of PTY output must not delay command responses. The event connection can buffer or drop independently of the command channel.

### Command connection messages

Request (client → server):
```json
{"jsonrpc":"2.0","id":1,"method":"pane.split","params":{"direction":"vertical"}}
```

Success response (server → client):
```json
{"jsonrpc":"2.0","id":1,"result":{"pane_id":"pane-5"}}
```

Error response (server → client):
```json
{"jsonrpc":"2.0","id":3,"error":{"code":-1,"message":"pane not found: xyz"}}
```

The `id` field is a monotonically increasing integer assigned by the client. Responses always carry the same `id` as the request they answer.

### Event connection messages

Subscribe (client → server — proper JSON-RPC request with `id`):
```json
{"jsonrpc":"2.0","id":1,"method":"subscribe","params":{"patterns":["pty.output","pty.exit"],"filter":{"pane_id":"pane-5"}}}
```

Acknowledgment (server → client — JSON-RPC response):
```json
{"jsonrpc":"2.0","id":1,"result":{"patterns":["pty.output","pty.exit"],"filter":{"pane_id":"pane-5"}}}
```

Event notification (server → client, continuous — JSON-RPC notification, no `id`):
```json
{"jsonrpc":"2.0","method":"pty.output","params":{"pane_id":"pane-5","data":"G1tI"}}
```

**Filter semantics:** The `filter` field is optional. If present, each key-value pair must match the event's params for the event to be forwarded. Pattern matching uses glob syntax (`pty.*` matches `pty.output` and `pty.exit`). Patterns match against the event name (the `source` field of `TypedEvent`).

## Method Surface

The daemon server routes ALL methods through `nexus_engine::dispatch()`. This spec requires extending `dispatch()` to cover all domains (PTY, session, keymap, commands, layout, chat) so the server has a single routing path. No method bypasses dispatch.

### Navigation

| Method | Params | Returns |
|---|---|---|
| `navigate.left` | — | `{focused: String}` |
| `navigate.right` | — | `{focused: String}` |
| `navigate.up` | — | `{focused: String}` |
| `navigate.down` | — | `{focused: String}` |

### Pane management

| Method | Params | Returns |
|---|---|---|
| `pane.split` | `direction: "vertical" \| "horizontal"` | `{pane_id: String}` |
| `pane.close` | `pane_id?: String` | `null` |
| `pane.zoom` | — | `null` |
| `pane.focus` | `pane_id: String` | `null` |
| `pane.resize` | `pane_id: String, ratio: f64` | `null` |
| `pane.new.terminal` | — | `{pane_id: String}` |
| `pane.new.chat` | — | `{pane_id: String}` |
| `pane.new.explorer` | — | `{pane_id: String}` |
| `pane.list` | — | `[{pane_id: String, pane_type: String}]` |

### PTY

| Method | Params | Returns |
|---|---|---|
| `pty.spawn` | `pane_id: String, cwd?: String, program?: String, args?: [String]` | `null` |
| `pty.write` | `pane_id: String, data: String` | `null` |
| `pty.resize` | `pane_id: String, cols: u16, rows: u16` | `null` |
| `pty.kill` | `pane_id: String` | `null` |

`pty.write` `data` is base64-encoded bytes. The client library handles encoding.

### Chat

| Method | Params | Returns |
|---|---|---|
| `chat.send` | `pane_id: String, message: String, cwd?: String` | `null` |

Chat output arrives as events on the event connection, not as the method response. The `chat` domain in `dispatch()` must be wired to `core.chat_send()` as part of this spec's implementation.

### Stack

| Method | Params | Returns |
|---|---|---|
| `stack.push` | `identity: String, name: String, command?: String, cwd?: String` | `{status, data}` |
| `stack.switch` | `identity: String, index?: u32` | `{status, data}` |
| `stack.replace` | `identity: String, name: String, command?: String` | `{status, data}` |
| `stack.close` | `identity: String` | `{status, data}` |
| `stack.adopt` | `identity: String, pane_handle: String` | `{status, data}` |
| `stack.tag` | `identity: String, tag: String` | `{status, data}` |
| `stack.untag` | `identity: String, tag: String` | `{status, data}` |
| `stack.rename` | `identity: String, name: String` | `{status, data}` |

All stack methods delegate to `core.handle_stack_op()`.

### Session

| Method | Params | Returns |
|---|---|---|
| `session.create` | `name: String, cwd: String` | `{session_id: String}` |
| `session.info` | — | `{name?: String}` |
| `session.list` | — | `[{name: String}]` |

### Keymap & Commands

| Method | Params | Returns |
|---|---|---|
| `keymap.get` | — | `[{key, action}]` |
| `commands.list` | — | `[{id, label, category, binding?}]` |

### Layout

| Method | Params | Returns |
|---|---|---|
| `layout.show` | — | `Value` (layout tree JSON) |

### Capabilities

| Method | Params | Returns |
|---|---|---|
| `capabilities.list` | `type?: "chat" \| "editor" \| "explorer"` | `[{name, type, priority, binary, available: bool}]` |

Returns registered adapters with their availability status. Without `type` filter, returns all. Enables surfaces to show what backends are available (e.g., "Claude available, OpenCode not found").

### Protocol

| Method | Params | Returns |
|---|---|---|
| `nexus.hello` | — | `{version: String, protocol: u32}` |

Optional handshake. Returns daemon version and protocol version number. Protocol version increments on breaking wire changes. Clients can check compatibility. Not required — clients that skip it get the current protocol.

### Generic dispatch

| Method | Params | Returns |
|---|---|---|
| `dispatch` | `command: String, args?: Object` | `Value` |

Catch-all that routes through `nexus_engine::dispatch()`. Useful for future commands not yet exposed as named methods.

## Event Types

Pushed on the event connection to subscribed clients.

| Event | Params |
|---|---|
| `pty.output` | `pane_id: String, data: String` (base64-encoded bytes) |
| `pty.exit` | `pane_id: String, exit_code: i32` |
| `agent.start` | `pane_id: String, backend: String` |
| `agent.text` | `pane_id: String, chunk: String` |
| `agent.done` | `pane_id: String, exit_code: i32, full_text: String` |
| `agent.error` | `pane_id: String, message: String` |
| `layout.changed` | `layout: Value` |
| `stack.changed` | `stack_id: String, op: String` |

PTY output uses base64 encoding on the wire (consistent with `pty.write`). The client library decodes to bytes.

## Event Bridge Architecture

The `EventBus` uses synchronous `Fn(&TypedEvent)` subscriber callbacks that fire inside `publish()` while the bus mutex is held. This is incompatible with async socket writes.

**Solution:** The event bridge uses an `mpsc` channel as a decoupling layer:

1. At daemon startup, create a `tokio::sync::mpsc::unbounded_channel::<TypedEvent>()`
2. Subscribe to `*.*` on the `EventBus` with a callback that clones the event and sends it through the `UnboundedSender` (non-blocking, never fails unless receiver dropped)
3. A tokio task reads from the `UnboundedReceiver` and fans out to active event connections, applying per-connection pattern + filter matching

This keeps the `EventBus` callback trivial (clone + send) and moves all async I/O to the tokio task.

```rust
// In daemon startup:
let (event_tx, mut event_rx) = tokio::sync::mpsc::unbounded_channel::<TypedEvent>();

// Subscribe on EventBus (sync callback):
bus.lock().unwrap().subscribe("*.*", move |event| {
    let _ = event_tx.send(event.clone());
});

// Tokio task fans out to connections:
tokio::spawn(async move {
    while let Some(event) = event_rx.recv().await {
        for conn in connections.lock().await.iter_mut() {
            if conn.matches(&event) {
                conn.write_event(&event).await;
            }
        }
    }
});
```

## Threading Model

`NexusCore` is behind `Arc<std::sync::Mutex<NexusCore>>` (not `tokio::sync::Mutex`). The daemon uses `tokio::task::spawn_blocking` for all engine calls to avoid blocking the tokio runtime:

```rust
let core = core.clone(); // Arc<Mutex<NexusCore>>
let result = tokio::task::spawn_blocking(move || {
    let mut core = core.lock().unwrap();
    dispatch(&mut core, &method, &params)
}).await??;
```

This is critical because `chat_send()` spawns background threads and `pty_spawn()` creates PTY processes — both can block briefly.

## Client Library (`nexus-client` crate)

**The client library lives in its own crate, not in `nexus-daemon`.** This prevents surfaces from transitively depending on the engine, tokio, portable-pty, etc. A CLI that sends JSON over a socket should be a tiny binary.

```
nexus-client/
├── Cargo.toml          (deps: nexus-core, serde, serde_json, base64)
├── src/
│   ├── lib.rs
│   ├── protocol.rs     — JSON-RPC 2.0 types (Request, Response, Notification)
│   ├── client.rs       — NexusClient (sync, command connection)
│   ├── events.rs       — EventSubscription (sync, event connection)
│   └── auto_launch.rs  — daemon auto-start logic
```

### Protocol types (`protocol.rs`)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,  // always "2.0"
    pub id: u64,
    pub method: String,
    #[serde(default)]
    pub params: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcNotification {
    pub jsonrpc: String,
    pub method: String,
    #[serde(default)]
    pub params: Value,
}
```

### NexusClient (`client.rs`)

Synchronous client for use by CLI, tmux adapter, and any non-async surface.

```rust
pub struct NexusClient {
    reader: BufReader<UnixStream>,
    writer: UnixStream,  // cloned from same fd
    next_id: AtomicU64,
}

impl NexusClient {
    /// Connect to daemon, auto-launching if needed.
    pub fn connect() -> Result<Self, NexusError>;

    /// Connect to a specific socket path (for testing).
    pub fn connect_to(path: &str) -> Result<Self, NexusError>;

    /// Send a JSON-RPC request and wait for the response.
    pub fn request(&self, method: &str, params: Value) -> Result<Value, NexusError>;

    // Convenience methods
    pub fn navigate(&self, direction: &str) -> Result<Value, NexusError>;
    pub fn split(&self, direction: &str) -> Result<Value, NexusError>;
    pub fn pty_spawn(&self, pane_id: &str, cwd: Option<&str>) -> Result<(), NexusError>;
    pub fn pty_write(&self, pane_id: &str, data: &[u8]) -> Result<(), NexusError>;
    pub fn pty_resize(&self, pane_id: &str, cols: u16, rows: u16) -> Result<(), NexusError>;
    pub fn pty_kill(&self, pane_id: &str) -> Result<(), NexusError>;
    pub fn chat_send(&self, pane_id: &str, message: &str, cwd: Option<&str>) -> Result<(), NexusError>;
    pub fn stack_op(&self, op: &str, payload: HashMap<String, String>) -> Result<Value, NexusError>;
    pub fn layout(&self) -> Result<Value, NexusError>;
    pub fn keymap(&self) -> Result<Value, NexusError>;
    pub fn commands(&self) -> Result<Value, NexusError>;
    pub fn pane_list(&self) -> Result<Value, NexusError>;
    pub fn capabilities(&self, cap_type: Option<&str>) -> Result<Value, NexusError>;
    pub fn hello(&self) -> Result<Value, NexusError>;
}
```

### EventSubscription (`events.rs`)

```rust
pub struct EventSubscription {
    reader: BufReader<UnixStream>,
    writer: UnixStream,
    next_id: AtomicU64,
}

impl EventSubscription {
    /// Connect to event socket and subscribe to patterns with optional filter.
    pub fn subscribe(
        patterns: &[&str],
        filter: Option<HashMap<String, Value>>,
    ) -> Result<Self, NexusError>;

    /// Update subscription (replaces current patterns/filter).
    pub fn resubscribe(
        &self,
        patterns: &[&str],
        filter: Option<HashMap<String, Value>>,
    ) -> Result<(), NexusError>;

    /// Block until next event arrives. Returns the JSON-RPC notification.
    pub fn next_event(&self) -> Result<JsonRpcNotification, NexusError>;
}
```

### Auto-launch implementation

```rust
fn find_daemon_bin() -> Result<std::path::PathBuf, NexusError> {
    // 1. Check NEXUS_DAEMON_BIN env var
    if let Ok(path) = std::env::var("NEXUS_DAEMON_BIN") {
        return Ok(path.into());
    }
    // 2. Check sibling of current executable
    if let Ok(exe) = std::env::current_exe() {
        let sibling = exe.parent().unwrap().join("nexus-daemon");
        if sibling.is_file() {
            return Ok(sibling);
        }
    }
    // 3. Fall back to PATH
    let ctx = SystemContext::from_login_shell();
    ctx.resolve_binary("nexus-daemon")
        .map(Into::into)
        .ok_or_else(|| NexusError::NotFound("nexus-daemon binary not found".into()))
}

fn auto_launch() -> Result<(), NexusError> {
    let daemon_bin = find_daemon_bin()?;
    std::process::Command::new(&daemon_bin)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()?;

    let socket = nexus_core::constants::socket_path();
    for _ in 0..60 {  // 60 * 50ms = 3s
        if std::path::Path::new(&socket).exists() {
            return Ok(());
        }
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
    Err(NexusError::Protocol("daemon failed to start within 3s".into()))
}
```

## Daemon Server (`nexus-daemon/src/server.rs`)

Tokio-based. Two `UnixListener`s bound to the command and event socket paths.

### Command handler

Per-connection tokio task:
1. Read lines from socket (NDJSON)
2. Parse as JSON-RPC request
3. `spawn_blocking` → lock `NexusCore`, call `dispatch(core, method, params)`
4. Serialize result as JSON-RPC response
5. Write response line to socket

### Event connection handler

Per-connection tokio task:
1. Read first line — parse as `subscribe` JSON-RPC request
2. Register connection in shared `Vec<EventConnection>` with patterns + filter
3. Send JSON-RPC response (acknowledgment)
4. Read subsequent lines — handle `subscribe` requests to update patterns/filter
5. On disconnect, remove from connection list

### Idle shutdown

A tokio task checks every 5s:
- Number of connected command clients (tracked via connection/drop counting)
- Number of active PTYs (`PtyManager` state)
- If both are zero for 30 consecutive seconds:
  1. Stop accepting new connections (drop listeners)
  2. Re-check conditions
  3. If still idle → graceful shutdown, cleanup socket + PID files

### Startup

```rust
#[tokio::main]
async fn main() {
    // 1. Parse --socket flag (optional override)
    // 2. Create socket directory if needed
    // 3. Remove stale socket files
    // 4. Write PID file
    // 5. SystemContext::from_login_shell()
    // 6. Construct adapters, register in CapabilityRegistry
    // 7. NexusCore::with_registry(NullMux, ctx)
    // 8. Create workspace "nexus"
    // 9. Set up event bridge (mpsc channel + EventBus subscriber)
    // 10. Bind command + event listeners
    // 11. tokio::select! { accept loops, ctrl_c, idle_shutdown }
    // 12. Cleanup: remove socket files, PID file
}
```

## Implementation Work Required in Existing Code

These changes to existing code are part of this spec's implementation scope:

1. **Extend `dispatch()` to cover ALL domains** — Add `pty`, `session`, `keymap`, `commands`, `layout`, `capabilities` domains. Wire `chat.send` to `core.chat_send()`. The daemon server must not have its own routing — everything goes through `dispatch()`.
2. **Add `events_socket_path()` to `constants.rs`** — Alongside existing `socket_path()`.
3. **Add `pane_list()` method to `LayoutTree`** — Flat list of pane IDs + types from the tree.
4. **Make `TypedEvent` implement `Clone`** — Required for the mpsc bridge pattern.
5. **Add `capabilities_list()` to `NexusCore`** — Queries registry for all adapters with availability status.
6. **Add `session_list()` to `NexusCore`** — Returns active sessions (currently only one, but the interface should support multiple).

## Crate Changes

### `nexus-client` — NEW crate

| File | Purpose |
|---|---|
| `protocol.rs` | JSON-RPC 2.0 types (Request, Response, Notification, Error) |
| `client.rs` | `NexusClient` — sync command connection with auto-launch |
| `events.rs` | `EventSubscription` — sync event connection with filtering |
| `auto_launch.rs` | Daemon binary discovery and spawn logic |
| `lib.rs` | Re-exports |

Dependencies: `nexus-core` (for `NexusError`, `socket_path`, `SystemContext`), `serde`, `serde_json`, `base64`.

### `nexus-daemon` — Major rework

| File | Change |
|---|---|
| `protocol.rs` | DELETE — moved to `nexus-client` |
| `client.rs` | DELETE — moved to `nexus-client` |
| `server.rs` | Two listeners, per-connection tokio tasks, spawn_blocking, all routing through `dispatch()` |
| `event_bridge.rs` | NEW — mpsc-based bridge from EventBus to filtered event connections |
| `main.rs` | Bootstrap engine with registry, set up event bridge, start listeners, idle shutdown |
| `lib.rs` | Just `pub mod server; pub mod event_bridge;` |

Dependencies: `nexus-engine`, `nexus-core`, `nexus-client` (for protocol types), `tokio`.

### `nexus-cli` — Thin client

Replace in-process `NexusCore` with `NexusClient::connect()`. Each subcommand becomes a single `client.request()` call.

| Before | After |
|---|---|
| `nexus-engine` dep | `nexus-client` dep |
| `NexusCore::new(NullMux)` | `NexusClient::connect()` |
| In-process method calls | `client.request("method", params)` |

### `nexus-tauri` — Thin client

Replace `NexusCore` ownership with `NexusClient`. Commands delegate to `client.request()`. Event subscription replaces direct `EventBus` subscription.

| Before | After |
|---|---|
| `AppState { core: Mutex<NexusCore> }` | `AppState { client: NexusClient }` |
| `nexus-engine` dep | `nexus-client` dep |
| `core.lock().layout.navigate(Nav::Left)` | `client.navigate("left")` |
| `core.lock().pty_spawn(...)` | `client.pty_spawn(...)` |
| Bus subscription in `setup()` | `EventSubscription` in background thread, emits Tauri events |

### `nexus-engine` — Extend dispatch

Add all domains to `dispatch()`: `pty`, `session`, `keymap`, `commands`, `layout`, `capabilities`. Wire `chat` domain to `core.chat_send()`. Add `capabilities.list` handler that queries the registry.

### `nexus-core` — Minimal changes

Add `events_socket_path()` to `constants.rs`. Ensure `TypedEvent` derives `Clone`.

## Dependency Graph (After)

```
nexus-core          (traits, types, constants, socket paths)
nexus-client        → nexus-core                           (protocol + sync client)
nexus-engine        → nexus-core                           (orchestration, process ownership)
nexus-daemon        → nexus-engine, nexus-core, nexus-client, tokio  (owns engine, serves socket)
nexus-cli           → nexus-client, nexus-core             (thin binary, no engine)
nexus-tauri         → nexus-client, nexus-core, tauri      (thin GUI, no engine)
nexus-tmux          → nexus-core                           (mux adapter)
nexus-editor        → nexus-core                           (editor adapter)
```

**Key property:** Surfaces (`nexus-cli`, `nexus-tauri`) depend on `nexus-client` — never on `nexus-engine` or `nexus-daemon`. Only the daemon depends on the engine. This means surface binaries are small and compile fast.

## Invariants

1. **Engine lives in daemon only.** No surface embeds `NexusCore`.
2. **All surfaces are equal peers.** Tauri, CLI, tmux — same client library, same protocol.
3. **Two connections, two concerns.** Commands are fast request/response. Events are filtered push streams. They don't interfere.
4. **Auto-launch is transparent.** First client to connect starts the daemon. No manual setup required.
5. **JSON-RPC 2.0 everywhere.** Both connections use the same wire format. No custom envelope.
6. **Event filtering is server-side.** Clients declare what they want. Server only sends matching events. No wasted bandwidth.
7. **spawn_blocking for engine calls.** Never hold the engine lock on a tokio worker thread.
8. **Single routing path.** All methods go through `dispatch()`. The daemon server never routes directly to engine methods.
9. **Surfaces never depend on the engine.** They depend on `nexus-client` only. Only the daemon depends on `nexus-engine`.

## Not In Scope

- TmuxMux real subprocess calls (still stubs)
- NeovimAdapter implementation
- Pane-as-OS-window surface process
- Authentication/authorization on the socket
- Multi-user or remote access
- Session persistence across daemon restarts
- TLS or encryption (local unix socket only)
