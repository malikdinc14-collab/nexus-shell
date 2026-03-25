# Daemon Socket Protocol — Design Spec

> Unlock tmux, CLI, and pane-as-OS-window surfaces by making the engine a standalone daemon that all surfaces connect to over Unix domain sockets using JSON-RPC 2.0.

## Context

The capability model port moved all tool logic into the engine. But Tauri still embeds `NexusCore` in-process — other surfaces (CLI, tmux, future OS-window panes) can't reach it. The daemon socket protocol makes the engine a shared service that all surfaces connect to as equal peers.

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

1. Spawn `nexus-daemon` as a detached background process
2. Poll for socket existence (50ms intervals, up to 3s)
3. Connect once socket appears
4. If socket never appears → `NexusError::Protocol("daemon failed to start")`

### Idle shutdown

Daemon shuts down after 30 seconds with no connected clients AND no active PTYs. A PID file at `$XDG_RUNTIME_DIR/nexus/nexus.pid` (or `/tmp/nexus-<uid>/nexus.pid`) tracks the daemon process.

## Wire Protocol

**JSON-RPC 2.0** over Unix domain sockets, newline-delimited (NDJSON). One JSON object per line, `\n` terminated.

### Two-connection model

Each client opens up to two connections:

1. **Command connection** (`nexus.sock`) — request/response, multiplexed by `id`. Client sends requests, server sends responses. Multiple requests can be in-flight simultaneously.

2. **Event connection** (`nexus-events.sock`) — server-push only. Client sends a single `subscribe` message, then receives a filtered stream of notifications. The event connection is optional — one-shot CLI commands don't need it.

**Why two connections:** Backpressure isolation. A pane dumping megabytes of PTY output must not delay command responses. The event connection can buffer or drop independently of the command channel.

### Command connection messages

Request (client → server):
```json
{"jsonrpc":"2.0","id":1,"method":"pane.split","params":{"direction":"vertical"}}
```

Success response (server → client):
```json
{"jsonrpc":"2.0","id":1,"result":{"pane_id":"pane-5","layout":{...}}}
```

Error response (server → client):
```json
{"jsonrpc":"2.0","id":3,"error":{"code":-1,"message":"pane not found: xyz"}}
```

The `id` field is a monotonically increasing integer assigned by the client. Responses always carry the same `id` as the request they answer.

### Event connection messages

Subscribe (client → server, sent once after connecting):
```json
{"jsonrpc":"2.0","method":"subscribe","params":{"patterns":["pty.output","pty.exit"],"filter":{"pane_id":"pane-5"}}}
```

Acknowledgment (server → client):
```json
{"jsonrpc":"2.0","method":"subscribed","params":{"patterns":["pty.output","pty.exit"],"filter":{"pane_id":"pane-5"}}}
```

Event notification (server → client, continuous):
```json
{"jsonrpc":"2.0","method":"pty.output","params":{"pane_id":"pane-5","data":[27,91,72]}}
```

Notifications have no `id` field — they are fire-and-forget from server to client.

**Filter semantics:** The `filter` field is optional. If present, each key-value pair must match the event's params for the event to be forwarded. Pattern matching uses the same glob syntax as `EventBus` (`pty.*` matches `pty.output` and `pty.exit`).

## Method Surface

All methods map 1:1 to existing `dispatch()` + engine methods.

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
| `pane.split` | `direction: "vertical" \| "horizontal"` | `{pane_id, layout}` |
| `pane.close` | `pane_id?: String` | `{layout}` |
| `pane.zoom` | — | `{layout}` |
| `pane.focus` | `pane_id: String` | `{layout}` |
| `pane.resize` | `pane_id: String, ratio: f64` | `{layout}` |
| `pane.new.terminal` | — | `{pane_id, layout}` |
| `pane.new.chat` | — | `{pane_id, layout}` |
| `pane.new.explorer` | — | `{pane_id, layout}` |

### PTY

| Method | Params | Returns |
|---|---|---|
| `pty.spawn` | `pane_id: String, cwd?: String, program?: String, args?: [String]` | `null` |
| `pty.write` | `pane_id: String, data: String` | `null` |
| `pty.resize` | `pane_id: String, cols: u16, rows: u16` | `null` |
| `pty.kill` | `pane_id: String` | `null` |

`pty.write` `data` is base64-encoded bytes.

### Chat

| Method | Params | Returns |
|---|---|---|
| `chat.send` | `pane_id: String, message: String, cwd?: String` | `null` |

Chat output arrives as events on the event connection, not as the method response.

### Stack

| Method | Params | Returns |
|---|---|---|
| `stack.push` | `identity: String, name: String, command?: String, cwd?: String` | `{status, data}` |
| `stack.switch` | `identity: String, index?: u32` | `{status, data}` |
| `stack.close` | `identity: String` | `{status, data}` |
| `stack.list` | `identity: String` | `{status, data}` |
| `stack.tag` | `identity: String, tag: String` | `{status, data}` |
| `stack.rename` | `identity: String, name: String` | `{status, data}` |

### Session

| Method | Params | Returns |
|---|---|---|
| `session.create` | `name: String, cwd: String` | `{session_id: String}` |
| `session.info` | — | `{name?: String}` |

### Keymap & Commands

| Method | Params | Returns |
|---|---|---|
| `keymap.get` | — | `[{key, action}]` |
| `commands.list` | — | `[{id, label, category, binding?}]` |

### Layout

| Method | Params | Returns |
|---|---|---|
| `layout.show` | — | `{layout: Value}` |

### Generic dispatch

| Method | Params | Returns |
|---|---|---|
| `dispatch` | `command: String, args?: Object` | `Value` |

Catch-all that routes through `nexus_engine::dispatch()`. All the above methods are convenience aliases — they all route through dispatch internally.

## Event Types

Pushed on the event connection to subscribed clients.

| Event | Params |
|---|---|
| `pty.output` | `pane_id: String, data: [u8]` |
| `pty.exit` | `pane_id: String, exit_code: i32` |
| `agent.start` | `pane_id: String, backend: String` |
| `agent.text` | `pane_id: String, chunk: String` |
| `agent.done` | `pane_id: String, exit_code: i32, full_text: String` |
| `agent.error` | `pane_id: String, message: String` |
| `layout.changed` | `layout: Value` |
| `stack.changed` | `stack_id: String, op: String` |

## Client Library (`nexus-daemon/src/client.rs`)

Synchronous client for use by CLI, tmux adapter, and any non-async surface.

```rust
pub struct NexusClient {
    cmd_stream: UnixStream,
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
    pub fn chat_send(&self, pane_id: &str, message: &str, cwd: Option<&str>) -> Result<(), NexusError>;
    pub fn stack_op(&self, op: &str, payload: HashMap<String, String>) -> Result<Value, NexusError>;
    pub fn layout(&self) -> Result<Value, NexusError>;
    pub fn keymap(&self) -> Result<Value, NexusError>;
    pub fn commands(&self) -> Result<Value, NexusError>;
}
```

```rust
pub struct EventSubscription {
    stream: UnixStream,
}

impl EventSubscription {
    /// Connect to event socket and subscribe to patterns with optional filter.
    pub fn subscribe(
        patterns: &[&str],
        filter: Option<HashMap<String, Value>>,
    ) -> Result<Self, NexusError>;

    /// Block until next event arrives. Returns the JSON-RPC notification.
    pub fn next_event(&self) -> Result<Notification, NexusError>;
}
```

### Auto-launch implementation

```rust
fn auto_launch() -> Result<(), NexusError> {
    let daemon_bin = std::env::current_exe()?
        .parent()
        .unwrap()
        .join("nexus-daemon");
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
3. Lock `NexusCore`, call `dispatch(core, method, params)`
4. Serialize result as JSON-RPC response
5. Write response line to socket

### Event bridge (`nexus-daemon/src/event_bridge.rs`)

Bridges `EventBus` → event socket connections.

The daemon subscribes to `*.*` on the `EventBus`. When an event fires, it iterates all active event connections, checks each connection's pattern + filter against the event, and writes matching events as JSON-RPC notifications.

Each event connection is tracked in a shared `Vec<EventConnection>` behind an `Arc<Mutex<>>`:

```rust
struct EventConnection {
    patterns: Vec<String>,
    filter: HashMap<String, Value>,
    writer: tokio::io::WriteHalf<UnixStream>,
}
```

### Idle shutdown

A tokio task checks every 5s:
- Number of connected command clients (tracked via connection/drop counting)
- Number of active PTYs (`PtyManager` state)
- If both are zero for 30 consecutive seconds → graceful shutdown

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
    // 9. Bind command + event listeners
    // 10. tokio::select! { accept loops, ctrl_c, idle_shutdown }
    // 11. Cleanup: remove socket files, PID file
}
```

## Crate Changes

### `nexus-daemon` — Major rework

| File | Change |
|---|---|
| `protocol.rs` | Replace custom Request/Response with JSON-RPC 2.0 types |
| `server.rs` | Two listeners, per-connection tokio tasks, dispatch through engine |
| `client.rs` | `NexusClient` (sync, command connection) + `EventSubscription` |
| `event_bridge.rs` | NEW — bridges EventBus to filtered event connections |
| `main.rs` | Bootstrap engine with registry, start listeners, idle shutdown |
| `lib.rs` | Add `pub mod event_bridge` |

### `nexus-cli` — Thin client

Replace in-process `NexusCore` with `NexusClient::connect()`. Each subcommand becomes a single `client.request()` call. Remove `nexus-engine` dependency, add `nexus-daemon` dependency.

| Before | After |
|---|---|
| `nexus-engine` dep | `nexus-daemon` dep (for `NexusClient`) |
| `NexusCore::new(NullMux)` | `NexusClient::connect()` |
| In-process method calls | `client.request("method", params)` |

### `nexus-tauri` — Thin client

Replace `NexusCore` ownership with `NexusClient`. Commands delegate to `client.request()`. Event subscription replaces direct `EventBus` subscription.

| Before | After |
|---|---|
| `AppState { core: Mutex<NexusCore> }` | `AppState { client: NexusClient, events: EventSubscription }` |
| `core.lock().layout.navigate(Nav::Left)` | `client.navigate("left")` |
| `core.lock().pty_spawn(...)` | `client.pty_spawn(...)` |
| Bus subscription in `setup()` | `EventSubscription::subscribe(["pty.*", "agent.*"])` in `setup()` |
| `nexus-engine` dep | `nexus-daemon` dep (for client) |

### `nexus-engine` — No changes

Engine doesn't know about sockets. It remains a library embedded by the daemon.

### `nexus-core` — Minimal changes

Add `events_socket_path()` to `constants.rs` alongside existing `socket_path()`.

## Dependency Graph (After)

```
nexus-core          (traits, types, constants)
nexus-engine        → nexus-core
nexus-daemon        → nexus-engine, nexus-core, tokio     (owns the engine)
nexus-cli           → nexus-daemon (client only), nexus-core
nexus-tauri         → nexus-daemon (client only), nexus-core, tauri
nexus-tmux          → nexus-core
nexus-editor        → nexus-core
```

## Invariants

1. **Engine lives in daemon only.** No surface embeds `NexusCore`.
2. **All surfaces are equal peers.** Tauri, CLI, tmux — same client library, same protocol.
3. **Two connections, two concerns.** Commands are fast request/response. Events are filtered push streams. They don't interfere.
4. **Auto-launch is transparent.** First client to connect starts the daemon. No manual setup required.
5. **JSON-RPC 2.0 everywhere.** Both connections use the same wire format. No custom envelope.
6. **Event filtering is server-side.** Clients declare what they want. Server only sends matching events. No wasted bandwidth.

## Not In Scope

- TmuxMux real subprocess calls (still stubs)
- NeovimAdapter implementation
- Pane-as-OS-window surface process
- Authentication/authorization on the socket
- Multi-user or remote access
- Session persistence across daemon restarts
- TLS or encryption (local unix socket only)
