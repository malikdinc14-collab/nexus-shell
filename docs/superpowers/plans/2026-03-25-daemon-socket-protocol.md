# Daemon Socket Protocol — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the engine a standalone daemon that all surfaces (Tauri, CLI, tmux, pane-as-OS-window) connect to over Unix sockets using JSON-RPC 2.0.

**Architecture:** `nexus-daemon` owns `NexusCore`. A new `nexus-client` crate provides sync JSON-RPC 2.0 client types. Two Unix sockets: command (request/response) and events (filtered push). All surfaces become thin clients using `nexus-client`. All methods route through `dispatch()`.

**Tech Stack:** Rust, tokio (daemon only), JSON-RPC 2.0, Unix domain sockets, NDJSON framing, base64 (PTY data encoding).

**Spec:** `docs/superpowers/specs/2026-03-25-daemon-socket-protocol-design.md`

---

## File Map

### New files

| File | Responsibility |
|---|---|
| `crates/nexus-client/Cargo.toml` | Crate manifest: deps on nexus-core, serde, serde_json, base64 |
| `crates/nexus-client/src/lib.rs` | Re-exports: protocol, client, events, auto_launch |
| `crates/nexus-client/src/protocol.rs` | JSON-RPC 2.0 types: Request, Response, Notification, Error |
| `crates/nexus-client/src/client.rs` | `NexusClient` — sync command connection with auto-launch |
| `crates/nexus-client/src/events.rs` | `EventSubscription` — sync event connection with filtering |
| `crates/nexus-client/src/auto_launch.rs` | Daemon binary discovery + spawn + socket poll |
| `crates/nexus-daemon/src/event_bridge.rs` | mpsc bridge from EventBus to filtered event connections |

### Modified files

| File | Change |
|---|---|
| `crates/Cargo.toml` | Add `"nexus-client"` to workspace members |
| `crates/nexus-core/src/constants.rs` | Add `events_socket_path()` and `pid_path()` |
| `crates/nexus-engine/src/layout.rs` | Add `LayoutNode::leaves()` returning `Vec<(String, PaneType)>` and `LayoutTree::pane_list()` |
| `crates/nexus-engine/src/dispatch.rs` | Extend with `pty`, `session`, `keymap`, `commands`, `layout`, `capabilities` domains; wire `chat.send` |
| `crates/nexus-engine/src/core.rs` | Add `capabilities_list()`, `session_list()`, `active_pty_count()` methods |
| `crates/nexus-engine/src/registry.rs` | Add `capabilities_list()` that returns JSON-serializable adapter info |
| `crates/nexus-engine/src/pty.rs` | Add `active_count()` method for idle shutdown |
| `crates/nexus-engine/Cargo.toml` | Add `base64 = "0.22"` dep for PTY data decode in dispatch |
| `crates/nexus-daemon/Cargo.toml` | Add dep on `nexus-client` |
| `crates/nexus-daemon/src/lib.rs` | Replace module declarations |
| `crates/nexus-daemon/src/server.rs` | Complete rewrite: two listeners, spawn_blocking, all through dispatch() |
| `crates/nexus-daemon/src/main.rs` | Complete rewrite: SystemContext, registry, event bridge, dual listeners, idle shutdown |
| `crates/nexus-cli/Cargo.toml` | Replace `nexus-engine` dep with `nexus-client` + `nexus-core` |
| `crates/nexus-cli/src/main.rs` | Complete rewrite: thin client using `NexusClient::connect()` |
| `crates/nexus-tauri/Cargo.toml` | Replace `nexus-engine` dep with `nexus-client` |
| `crates/nexus-tauri/src/main.rs` | Complete rewrite: thin client, EventSubscription in background thread |
| `crates/nexus-tauri/src/commands.rs` | Complete rewrite: delegate to `client.request()` calls |

### Deleted files

| File | Reason |
|---|---|
| `crates/nexus-daemon/src/protocol.rs` | Replaced by `nexus-client/src/protocol.rs` |
| `crates/nexus-daemon/src/client.rs` | Replaced by `nexus-client/src/client.rs` |

---

## Phase 1: Foundation (Tasks 1-4)

Build the new `nexus-client` crate and extend the engine's dispatch layer to cover all domains.

---

### Task 1: nexus-client crate — protocol types

Create the `nexus-client` crate with JSON-RPC 2.0 protocol types. These types are used by both client and server.

**Files:**
- Create: `crates/nexus-client/Cargo.toml`
- Create: `crates/nexus-client/src/lib.rs`
- Create: `crates/nexus-client/src/protocol.rs`
- Modify: `crates/Cargo.toml` (add workspace member)

- [ ] **Step 1: Write the failing test for protocol types**

Create `crates/nexus-client/src/protocol.rs` with types and tests:

```rust
//! JSON-RPC 2.0 wire types for the Nexus daemon protocol.

use serde::{Deserialize, Serialize};

/// JSON-RPC 2.0 request (client -> server).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: u64,
    pub method: String,
    #[serde(default, skip_serializing_if = "serde_json::Value::is_null")]
    pub params: serde_json::Value,
}

impl JsonRpcRequest {
    pub fn new(id: u64, method: &str, params: serde_json::Value) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            id,
            method: method.into(),
            params,
        }
    }
}

/// JSON-RPC 2.0 response (server -> client).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
}

impl JsonRpcResponse {
    pub fn success(id: u64, result: serde_json::Value) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            id,
            result: Some(result),
            error: None,
        }
    }

    pub fn error(id: u64, code: i32, message: &str) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            id,
            result: None,
            error: Some(JsonRpcError {
                code,
                message: message.into(),
            }),
        }
    }
}

/// JSON-RPC 2.0 error object.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
}

/// JSON-RPC 2.0 notification (server -> client, no id).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcNotification {
    pub jsonrpc: String,
    pub method: String,
    #[serde(default, skip_serializing_if = "serde_json::Value::is_null")]
    pub params: serde_json::Value,
}

impl JsonRpcNotification {
    pub fn new(method: &str, params: serde_json::Value) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            method: method.into(),
            params,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn request_serializes_to_jsonrpc() {
        let req = JsonRpcRequest::new(1, "pane.split", serde_json::json!({"direction": "vertical"}));
        let json = serde_json::to_string(&req).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed["jsonrpc"], "2.0");
        assert_eq!(parsed["id"], 1);
        assert_eq!(parsed["method"], "pane.split");
        assert_eq!(parsed["params"]["direction"], "vertical");
    }

    #[test]
    fn request_roundtrips() {
        let req = JsonRpcRequest::new(42, "navigate.left", serde_json::Value::Null);
        let json = serde_json::to_string(&req).unwrap();
        let back: JsonRpcRequest = serde_json::from_str(&json).unwrap();
        assert_eq!(back.id, 42);
        assert_eq!(back.method, "navigate.left");
    }

    #[test]
    fn success_response_has_result_no_error() {
        let resp = JsonRpcResponse::success(1, serde_json::json!({"pane_id": "pane-5"}));
        let json = serde_json::to_string(&resp).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed["result"]["pane_id"], "pane-5");
        assert!(parsed.get("error").is_none());
    }

    #[test]
    fn error_response_has_error_no_result() {
        let resp = JsonRpcResponse::error(3, -1, "pane not found: xyz");
        let json = serde_json::to_string(&resp).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert!(parsed.get("result").is_none());
        assert_eq!(parsed["error"]["code"], -1);
        assert_eq!(parsed["error"]["message"], "pane not found: xyz");
    }

    #[test]
    fn notification_has_no_id() {
        let notif = JsonRpcNotification::new("pty.output", serde_json::json!({"pane_id": "p1", "data": "aGVsbG8="}));
        let json = serde_json::to_string(&notif).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert!(parsed.get("id").is_none());
        assert_eq!(parsed["method"], "pty.output");
    }

    #[test]
    fn request_null_params_omitted() {
        let req = JsonRpcRequest::new(1, "pane.zoom", serde_json::Value::Null);
        let json = serde_json::to_string(&req).unwrap();
        assert!(!json.contains("params"));
    }
}
```

- [ ] **Step 2: Create Cargo.toml and lib.rs**

`crates/nexus-client/Cargo.toml`:
```toml
[package]
name = "nexus-client"
version = "0.1.0"
edition = "2021"
description = "Nexus daemon client library — JSON-RPC 2.0 over Unix sockets"

[dependencies]
nexus-core = { path = "../nexus-core" }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
base64 = "0.22"
```

`crates/nexus-client/src/lib.rs`:
```rust
//! Nexus client library — sync JSON-RPC 2.0 client for the Nexus daemon.
//!
//! Provides `NexusClient` (command connection) and `EventSubscription`
//! (filtered event stream). Surfaces (CLI, Tauri, tmux) depend on this
//! crate — never on the engine directly.

pub mod protocol;
```

- [ ] **Step 3: Add workspace member**

In `crates/Cargo.toml`, add `"nexus-client"` to the `members` list.

- [ ] **Step 4: Run tests to verify**

Run: `cd crates && cargo test -p nexus-client`
Expected: All 6 protocol tests pass.

- [ ] **Step 5: Commit**

```bash
git add crates/nexus-client/ crates/Cargo.toml
git commit -m "feat(client): create nexus-client crate with JSON-RPC 2.0 protocol types"
```

---

### Task 2: nexus-core — add socket path helpers

Add `events_socket_path()` and `pid_path()` to constants.

**Files:**
- Modify: `crates/nexus-core/src/constants.rs`

- [ ] **Step 1: Write the failing tests**

Add tests at the end of the existing `tests` module in `crates/nexus-core/src/constants.rs`:

```rust
#[cfg(unix)]
#[test]
fn events_socket_path_returns_events_sock() {
    let p = events_socket_path();
    assert_eq!(p.file_name().unwrap(), "nexus-events.sock");
    // Same parent directory as command socket
    assert_eq!(p.parent(), socket_path().parent());
}

#[cfg(unix)]
#[test]
fn pid_path_returns_pid_file() {
    let p = pid_path();
    assert_eq!(p.file_name().unwrap(), "nexus.pid");
    assert_eq!(p.parent(), socket_path().parent());
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd crates && cargo test -p nexus-core -- constants`
Expected: FAIL — `events_socket_path` and `pid_path` not found.

- [ ] **Step 3: Implement the functions**

Add after the existing `socket_path()` function:

```rust
/// Compute the event socket path (sibling of command socket).
#[cfg(unix)]
pub fn events_socket_path() -> PathBuf {
    let mut p = socket_path();
    p.set_file_name("nexus-events.sock");
    p
}

#[cfg(not(unix))]
pub fn events_socket_path() -> PathBuf {
    PathBuf::from(r"\\.\pipe\nexus-events")
}

/// Compute the PID file path (sibling of command socket).
#[cfg(unix)]
pub fn pid_path() -> PathBuf {
    let mut p = socket_path();
    p.set_file_name("nexus.pid");
    p
}

#[cfg(not(unix))]
pub fn pid_path() -> PathBuf {
    PathBuf::from(r"\\.\pipe\nexus.pid")
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd crates && cargo test -p nexus-core -- constants`
Expected: All constants tests pass.

- [ ] **Step 5: Commit**

```bash
git add crates/nexus-core/src/constants.rs
git commit -m "feat(core): add events_socket_path() and pid_path() to constants"
```

---

### Task 3: nexus-engine — extend layout and core for dispatch

Add `LayoutNode::leaves()`, `LayoutTree::pane_list()`, `NexusCore::capabilities_list()`, `NexusCore::session_list()`, `PtyManager::active_count()`.

**Files:**
- Modify: `crates/nexus-engine/src/layout.rs`
- Modify: `crates/nexus-engine/src/core.rs`
- Modify: `crates/nexus-engine/src/registry.rs`
- Modify: `crates/nexus-engine/src/pty.rs`

- [ ] **Step 1: Write failing test for `LayoutNode::leaves()`**

Add to the test module in `crates/nexus-engine/src/layout.rs`:

```rust
#[test]
fn leaves_returns_id_and_type() {
    let tree = LayoutNode::split(
        Direction::Vertical,
        0.5,
        LayoutNode::leaf("p1", PaneType::Terminal),
        LayoutNode::leaf("p2", PaneType::Chat),
    );
    let leaves = tree.leaves();
    assert_eq!(leaves.len(), 2);
    assert_eq!(leaves[0], ("p1".into(), PaneType::Terminal));
    assert_eq!(leaves[1], ("p2".into(), PaneType::Chat));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd crates && cargo test -p nexus-engine -- leaves_returns_id_and_type`
Expected: FAIL — method `leaves` not found.

- [ ] **Step 3: Implement `LayoutNode::leaves()`**

Add to `impl LayoutNode` in `layout.rs`, after `leaf_ids()`:

```rust
/// Collect all leaves as (id, pane_type) pairs in tree order.
pub fn leaves(&self) -> Vec<(String, PaneType)> {
    match self {
        LayoutNode::Leaf { id, pane_type } => vec![(id.clone(), *pane_type)],
        LayoutNode::Split { left, right, .. } => {
            let mut out = left.leaves();
            out.extend(right.leaves());
            out
        }
    }
}
```

- [ ] **Step 4: Write failing test for `LayoutTree::pane_list()`**

Add to the test module in `layout.rs`:

```rust
#[test]
fn pane_list_returns_json_array() {
    let mut tree = LayoutTree::default_layout();
    // default_layout has 4 panes; split adds a 5th
    tree.split_focused(Direction::Vertical, PaneType::Chat);
    let list = tree.pane_list();
    assert!(list.is_array());
    let arr = list.as_array().unwrap();
    assert_eq!(arr.len(), 5);
    assert!(arr[0].get("pane_id").is_some());
    assert!(arr[0].get("pane_type").is_some());
}
```

- [ ] **Step 5: Implement `LayoutTree::pane_list()`**

Add to `impl LayoutTree` in `layout.rs`:

```rust
/// Flat list of all panes as JSON: [{pane_id, pane_type}, ...]
pub fn pane_list(&self) -> serde_json::Value {
    let leaves = self.root.leaves();
    let arr: Vec<serde_json::Value> = leaves
        .into_iter()
        .map(|(id, pt)| serde_json::json!({"pane_id": id, "pane_type": pt.as_str()}))
        .collect();
    serde_json::Value::Array(arr)
}
```

- [ ] **Step 6: Run layout tests**

Run: `cd crates && cargo test -p nexus-engine -- layout`
Expected: All pass.

- [ ] **Step 7: Add `active_count()` to PtyManager**

Read `crates/nexus-engine/src/pty.rs` to find the struct fields, then add:

```rust
/// Number of active PTY sessions.
pub fn active_count(&self) -> usize {
    self.sessions.len()
}
```

And add a test:

```rust
#[test]
fn active_count_starts_at_zero() {
    let mgr = PtyManager::new();
    assert_eq!(mgr.active_count(), 0);
}
```

- [ ] **Step 8: Add `capabilities_list()` to CapabilityRegistry**

Add to `impl CapabilityRegistry` in `registry.rs`:

```rust
/// Return all registered adapters as JSON, optionally filtered by type.
pub fn capabilities_list(&self, type_filter: Option<&str>) -> serde_json::Value {
    let mut result = Vec::new();
    let add = |result: &mut Vec<serde_json::Value>, cap: &dyn Capability| {
        let m = cap.manifest();
        result.push(serde_json::json!({
            "name": m.name,
            "type": match m.capability_type {
                nexus_core::capability::CapabilityType::Chat => "chat",
                nexus_core::capability::CapabilityType::Editor => "editor",
                nexus_core::capability::CapabilityType::Explorer => "explorer",
                nexus_core::capability::CapabilityType::Multiplexer => "multiplexer",
            },
            "priority": m.priority,
            "binary": m.binary,
            "available": cap.is_available(),
        }));
    };

    if type_filter.is_none() || type_filter == Some("chat") {
        for c in &self.chat {
            add(&mut result, c.as_ref());
        }
    }
    if type_filter.is_none() || type_filter == Some("editor") {
        for c in &self.editor {
            add(&mut result, c.as_ref());
        }
    }
    if type_filter.is_none() || type_filter == Some("explorer") {
        for c in &self.explorer {
            add(&mut result, c.as_ref());
        }
    }

    serde_json::Value::Array(result)
}
```

And add a test:

```rust
#[test]
fn capabilities_list_all() {
    let mut reg = CapabilityRegistry::new(empty_ctx());
    reg.register_chat(Box::new(StubChat::new("claude", 100, true)));
    let list = reg.capabilities_list(None);
    let arr = list.as_array().unwrap();
    assert_eq!(arr.len(), 1);
    assert_eq!(arr[0]["name"], "claude");
    assert_eq!(arr[0]["available"], true);
}

#[test]
fn capabilities_list_filtered() {
    let mut reg = CapabilityRegistry::new(empty_ctx());
    reg.register_chat(Box::new(StubChat::new("claude", 100, true)));
    reg.register_explorer(Box::new(StubExplorer {
        manifest: AdapterManifest {
            name: "fs",
            capability_type: CapabilityType::Explorer,
            priority: 50,
            binary: "",
        },
    }));
    let chat_only = reg.capabilities_list(Some("chat"));
    assert_eq!(chat_only.as_array().unwrap().len(), 1);
    let explorer_only = reg.capabilities_list(Some("explorer"));
    assert_eq!(explorer_only.as_array().unwrap().len(), 1);
}
```

- [ ] **Step 9: Add `stack_list` to `handle_stack_op` in NexusCore**

The existing `handle_stack_op` doesn't handle "list". Add a match arm in `core.rs` inside `handle_stack_op`:

```rust
"list" => self.stack_list(payload),
```

And add the method:

```rust
fn stack_list(&self, payload: &HashMap<String, String>) -> OpResult {
    let identity = payload.get("identity").map(|s| s.as_str()).unwrap_or("");
    match self.stacks.get_by_identity(identity) {
        Some((_sid, stack)) => {
            let tabs: Vec<serde_json::Value> = stack.tabs.iter().enumerate().map(|(i, tab)| {
                serde_json::json!({
                    "index": i,
                    "name": tab.name,
                    "pane_handle": tab.pane_handle,
                    "is_active": tab.is_active,
                })
            }).collect();
            OpResult::ok_with("tabs", serde_json::Value::Array(tabs))
        }
        None => OpResult::error("not_found"),
    }
}
```

- [ ] **Step 10: Add `capabilities_list()` and `session_list()` to NexusCore**

Add to `impl NexusCore` in `core.rs`:

```rust
/// List all registered adapters with availability.
pub fn capabilities_list(&self, type_filter: Option<&str>) -> serde_json::Value {
    match &self.registry {
        Some(reg) => reg.capabilities_list(type_filter),
        None => serde_json::json!([]),
    }
}

/// List active sessions.
pub fn session_list(&self) -> Vec<serde_json::Value> {
    match &self.session {
        Some(name) => vec![serde_json::json!({"name": name})],
        None => vec![],
    }
}

/// Number of active PTY processes.
pub fn active_pty_count(&self) -> usize {
    self.pty.active_count()
}
```

- [ ] **Step 11: Run all engine tests**

Run: `cd crates && cargo test -p nexus-engine`
Expected: All pass.

- [ ] **Step 12: Commit**

```bash
git add crates/nexus-engine/ crates/nexus-core/
git commit -m "feat(engine): add pane_list, capabilities_list, session_list, active_pty_count"
```

---

### Task 4: nexus-engine — extend dispatch() to cover all domains

Wire pty, session, keymap, commands, layout, capabilities into `dispatch()`. Wire `chat.send` to `core.chat_send()`.

**Files:**
- Modify: `crates/nexus-engine/src/dispatch.rs`

- [ ] **Step 1: Write failing tests for new domains**

Add to the test module in `dispatch.rs`:

```rust
#[test]
fn dispatch_layout_show() {
    let mut core = make_core();
    let result = dispatch(&mut core, "layout.show", &HashMap::new());
    assert!(result.is_ok());
}

#[test]
fn dispatch_pane_list() {
    let mut core = make_core();
    let result = dispatch(&mut core, "pane.list", &HashMap::new());
    assert!(result.is_ok());
    let val = result.unwrap();
    assert!(val.is_array());
}

#[test]
fn dispatch_session_info() {
    let mut core = make_core();
    let result = dispatch(&mut core, "session.info", &HashMap::new());
    assert!(result.is_ok());
}

#[test]
fn dispatch_session_create() {
    let mut core = make_core();
    let mut args = HashMap::new();
    args.insert("name".to_string(), serde_json::json!("test2"));
    args.insert("cwd".to_string(), serde_json::json!("/tmp"));
    let result = dispatch(&mut core, "session.create", &args);
    assert!(result.is_ok());
}

#[test]
fn dispatch_session_list() {
    let mut core = make_core();
    let result = dispatch(&mut core, "session.list", &HashMap::new());
    assert!(result.is_ok());
}

#[test]
fn dispatch_keymap_get() {
    let mut core = make_core();
    let result = dispatch(&mut core, "keymap.get", &HashMap::new());
    assert!(result.is_ok());
}

#[test]
fn dispatch_commands_list() {
    let mut core = make_core();
    let result = dispatch(&mut core, "commands.list", &HashMap::new());
    assert!(result.is_ok());
}

#[test]
fn dispatch_capabilities_list() {
    let mut core = make_core();
    let result = dispatch(&mut core, "capabilities.list", &HashMap::new());
    assert!(result.is_ok());
}

#[test]
fn dispatch_pty_spawn_and_kill() {
    let ctx = nexus_core::capability::SystemContext {
        path: std::env::var("PATH").unwrap_or_default(),
        shell: "/bin/zsh".into(),
    };
    let mut core = NexusCore::with_registry(Box::new(NullMux::new()), ctx);
    core.create_workspace("test", "/tmp");

    let mut args = HashMap::new();
    args.insert("pane_id".to_string(), serde_json::json!("test-pane"));
    let spawn = dispatch(&mut core, "pty.spawn", &args);
    assert!(spawn.is_ok());

    let kill = dispatch(&mut core, "pty.kill", &args);
    assert!(kill.is_ok());
}

#[test]
fn dispatch_nexus_hello() {
    let mut core = make_core();
    let result = dispatch(&mut core, "nexus.hello", &HashMap::new());
    assert!(result.is_ok());
    let val = result.unwrap();
    assert!(val.get("version").is_some());
    assert!(val.get("protocol").is_some());
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd crates && cargo test -p nexus-engine -- dispatch`
Expected: FAIL — unknown domain errors for layout, session, keymap, etc.

- [ ] **Step 3: Add `base64` dep to nexus-engine**

Add to `crates/nexus-engine/Cargo.toml`:
```toml
base64 = "0.22"
```

- [ ] **Step 4: Implement new domain handlers**

Replace the `dispatch()` match block to add all domains:

```rust
match domain {
    "navigate" => handle_navigate(core, action),
    "pane" => handle_pane(core, action, args),
    "stack" => handle_stack(core, action, args),
    "chat" => handle_chat(core, action, args),
    "pty" => handle_pty(core, action, args),
    "session" => handle_session(core, action, args),
    "keymap" => handle_keymap(core, action),
    "commands" => handle_commands(core, action),
    "layout" => handle_layout(core, action, args),
    "capabilities" => handle_capabilities(core, action, args),
    "nexus" => handle_nexus(action),
    _ => Err(NexusError::NotFound(format!("unknown domain: {domain}"))),
}
```

Add the handler functions:

```rust
fn handle_pty(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    let str_arg = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match action {
        "spawn" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.spawn requires pane_id".into())
            })?;
            let cwd = str_arg("cwd");
            let program = str_arg("program");
            let prog_args: Option<Vec<String>> = args.get("args")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect());

            if let (Some(prog), Some(pargs)) = (program, prog_args) {
                core.pty_spawn_cmd(&pane_id, cwd.as_deref().unwrap_or("/tmp"), &prog, &pargs)
                    .map_err(|e| NexusError::InvalidState(e))?;
            } else {
                core.pty_spawn(&pane_id, cwd.as_deref())
                    .map_err(|e| NexusError::InvalidState(e))?;
            }
            Ok(serde_json::Value::Null)
        }
        "write" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.write requires pane_id".into())
            })?;
            let data_b64 = str_arg("data").ok_or_else(|| {
                NexusError::InvalidState("pty.write requires data".into())
            })?;
            // Decode base64 wire encoding back to raw bytes
            use base64::Engine;
            let bytes = base64::engine::general_purpose::STANDARD.decode(&data_b64)
                .map_err(|e| NexusError::InvalidState(format!("base64 decode: {e}")))?;
            let decoded = String::from_utf8_lossy(&bytes);
            core.pty_write(&pane_id, &decoded)
                .map_err(|e| NexusError::InvalidState(e))?;
            Ok(serde_json::Value::Null)
        }
        "resize" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.resize requires pane_id".into())
            })?;
            let cols = args.get("cols").and_then(|v| v.as_u64()).unwrap_or(80) as u16;
            let rows = args.get("rows").and_then(|v| v.as_u64()).unwrap_or(24) as u16;
            core.pty_resize(&pane_id, cols, rows)
                .map_err(|e| NexusError::InvalidState(e))?;
            Ok(serde_json::Value::Null)
        }
        "kill" => {
            let pane_id = str_arg("pane_id").ok_or_else(|| {
                NexusError::InvalidState("pty.kill requires pane_id".into())
            })?;
            core.pty_kill(&pane_id)
                .map_err(|e| NexusError::InvalidState(e))?;
            Ok(serde_json::Value::Null)
        }
        _ => Err(NexusError::NotFound(format!("unknown pty action: {action}"))),
    }
}

fn handle_session(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "create" => {
            let name = args.get("name").and_then(|v| v.as_str()).unwrap_or("nexus");
            let cwd = args.get("cwd").and_then(|v| v.as_str()).unwrap_or("/tmp");
            let session_id = core.create_workspace(name, cwd);
            Ok(serde_json::json!({"session_id": session_id}))
        }
        "info" => {
            Ok(serde_json::json!({"name": core.session()}))
        }
        "list" => {
            Ok(serde_json::Value::Array(core.session_list()))
        }
        _ => Err(NexusError::NotFound(format!("unknown session action: {action}"))),
    }
}

fn handle_keymap(
    core: &mut NexusCore,
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "get" => {
            serde_json::to_value(core.get_keymap())
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown keymap action: {action}"))),
    }
}

fn handle_commands(
    core: &mut NexusCore,
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "list" => {
            serde_json::to_value(core.get_commands())
                .map_err(|e| NexusError::InvalidState(e.to_string()))
        }
        _ => Err(NexusError::NotFound(format!("unknown commands action: {action}"))),
    }
}

fn handle_layout(
    core: &mut NexusCore,
    action: &str,
    _args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "show" => Ok(core.layout.to_json()),
        _ => Err(NexusError::NotFound(format!("unknown layout action: {action}"))),
    }
}

fn handle_capabilities(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "list" => {
            let type_filter = args.get("type").and_then(|v| v.as_str());
            Ok(core.capabilities_list(type_filter))
        }
        _ => Err(NexusError::NotFound(format!("unknown capabilities action: {action}"))),
    }
}

fn handle_nexus(
    action: &str,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "hello" => Ok(serde_json::json!({
            "version": env!("CARGO_PKG_VERSION"),
            "protocol": 1,
        })),
        _ => Err(NexusError::NotFound(format!("unknown nexus action: {action}"))),
    }
}
```

Also wire `chat.send` in the existing `handle_chat`:

```rust
fn handle_chat(
    core: &mut NexusCore,
    action: &str,
    args: &HashMap<String, serde_json::Value>,
) -> Result<serde_json::Value, NexusError> {
    match action {
        "send" => {
            let pane_id = args.get("pane_id").and_then(|v| v.as_str()).ok_or_else(|| {
                NexusError::InvalidState("chat.send requires pane_id".into())
            })?;
            let message = args.get("message").and_then(|v| v.as_str()).ok_or_else(|| {
                NexusError::InvalidState("chat.send requires message".into())
            })?;
            let cwd = args.get("cwd").and_then(|v| v.as_str()).unwrap_or("/tmp");
            core.chat_send(pane_id, message, cwd)
                .map_err(|e| NexusError::InvalidState(e))?;
            Ok(serde_json::Value::Null)
        }
        _ => Err(NexusError::NotFound(format!("unknown chat action: {action}"))),
    }
}
```

Also add `pane.list` to the existing `handle_pane` function — add a match arm before the `_ if action.starts_with("new.")` arm:

```rust
"list" => Ok(core.layout.pane_list()),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd crates && cargo test -p nexus-engine -- dispatch`
Expected: All dispatch tests pass (old + new).

- [ ] **Step 6: Commit**

```bash
git add crates/nexus-engine/src/dispatch.rs crates/nexus-engine/Cargo.toml
git commit -m "feat(engine): extend dispatch() with pty, session, keymap, commands, layout, capabilities, nexus domains"
```

---

## Phase 2: Daemon Server (Tasks 5-7)

Build the nexus-client connection types, event bridge, and rewrite the daemon.

---

### Task 5: nexus-client — NexusClient and EventSubscription

Add the sync client, event subscription, and auto-launch logic.

**Files:**
- Create: `crates/nexus-client/src/client.rs`
- Create: `crates/nexus-client/src/events.rs`
- Create: `crates/nexus-client/src/auto_launch.rs`
- Modify: `crates/nexus-client/src/lib.rs`

- [ ] **Step 1: Implement auto_launch module**

`crates/nexus-client/src/auto_launch.rs`:
```rust
//! Daemon auto-start logic — find and launch nexus-daemon if no socket exists.

use nexus_core::NexusError;
use std::path::{Path, PathBuf};

/// Locate the nexus-daemon binary.
pub fn find_daemon_bin() -> Result<PathBuf, NexusError> {
    // 1. NEXUS_DAEMON_BIN env var
    if let Ok(path) = std::env::var("NEXUS_DAEMON_BIN") {
        let p = PathBuf::from(&path);
        if p.is_file() {
            return Ok(p);
        }
    }
    // 2. Sibling of current executable
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let sibling = parent.join("nexus-daemon");
            if sibling.is_file() {
                return Ok(sibling);
            }
        }
    }
    // 3. PATH lookup
    let path_var = std::env::var("PATH").unwrap_or_default();
    for dir in std::env::split_paths(&path_var) {
        let candidate = dir.join("nexus-daemon");
        if candidate.is_file() {
            return Ok(candidate);
        }
    }
    Err(NexusError::NotFound("nexus-daemon binary not found".into()))
}

/// Spawn the daemon and wait for the socket to appear.
pub fn auto_launch(socket_path: &Path) -> Result<(), NexusError> {
    let daemon_bin = find_daemon_bin()?;

    std::process::Command::new(&daemon_bin)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .map_err(|e| NexusError::Protocol(format!("failed to spawn daemon: {e}")))?;

    // Poll for socket (50ms * 60 = 3s)
    for _ in 0..60 {
        if socket_path.exists() {
            return Ok(());
        }
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
    Err(NexusError::Protocol("daemon failed to start within 3s".into()))
}
```

- [ ] **Step 2: Implement NexusClient**

`crates/nexus-client/src/client.rs`:
```rust
//! NexusClient — synchronous JSON-RPC 2.0 client for the command socket.

use crate::protocol::{JsonRpcRequest, JsonRpcResponse};
use nexus_core::NexusError;
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixStream;
use std::sync::atomic::{AtomicU64, Ordering};

/// Synchronous client for the Nexus daemon command socket.
pub struct NexusClient {
    reader: BufReader<UnixStream>,
    writer: UnixStream,
    next_id: AtomicU64,
}

impl NexusClient {
    /// Connect to daemon, auto-launching if needed.
    pub fn connect() -> Result<Self, NexusError> {
        let path = nexus_core::constants::socket_path();
        if !path.exists() {
            crate::auto_launch::auto_launch(&path)?;
        }
        Self::connect_to(path.to_str().unwrap_or(""))
    }

    /// Connect to a specific socket path (for testing).
    pub fn connect_to(path: &str) -> Result<Self, NexusError> {
        let stream = UnixStream::connect(path)
            .map_err(|e| NexusError::Protocol(format!("connect failed: {e}")))?;
        let reader = BufReader::new(stream.try_clone()
            .map_err(|e| NexusError::Protocol(format!("clone stream: {e}")))?);
        Ok(Self {
            reader,
            writer: stream,
            next_id: AtomicU64::new(1),
        })
    }

    /// Send a JSON-RPC request and wait for the response.
    pub fn request(&mut self, method: &str, params: serde_json::Value) -> Result<serde_json::Value, NexusError> {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed);
        let req = JsonRpcRequest::new(id, method, params);
        let mut line = serde_json::to_string(&req)
            .map_err(|e| NexusError::Protocol(format!("serialize: {e}")))?;
        line.push('\n');
        self.writer.write_all(line.as_bytes())
            .map_err(|e| NexusError::Protocol(format!("write: {e}")))?;

        let mut buf = String::new();
        self.reader.read_line(&mut buf)
            .map_err(|e| NexusError::Protocol(format!("read: {e}")))?;

        let resp: JsonRpcResponse = serde_json::from_str(&buf)
            .map_err(|e| NexusError::Protocol(format!("parse response: {e}")))?;

        if let Some(err) = resp.error {
            return Err(NexusError::Protocol(err.message));
        }
        Ok(resp.result.unwrap_or(serde_json::Value::Null))
    }

    // -- Convenience methods --

    pub fn navigate(&mut self, direction: &str) -> Result<serde_json::Value, NexusError> {
        self.request(&format!("navigate.{direction}"), serde_json::Value::Null)
    }

    pub fn split(&mut self, direction: &str) -> Result<serde_json::Value, NexusError> {
        self.request("pane.split", serde_json::json!({"direction": direction}))
    }

    pub fn pane_list(&mut self) -> Result<serde_json::Value, NexusError> {
        self.request("pane.list", serde_json::Value::Null)
    }

    pub fn pty_spawn(&mut self, pane_id: &str, cwd: Option<&str>) -> Result<(), NexusError> {
        let mut params = serde_json::json!({"pane_id": pane_id});
        if let Some(cwd) = cwd {
            params["cwd"] = serde_json::json!(cwd);
        }
        self.request("pty.spawn", params)?;
        Ok(())
    }

    pub fn pty_write(&mut self, pane_id: &str, data: &[u8]) -> Result<(), NexusError> {
        use base64::Engine;
        let encoded = base64::engine::general_purpose::STANDARD.encode(data);
        self.request("pty.write", serde_json::json!({"pane_id": pane_id, "data": encoded}))?;
        Ok(())
    }

    pub fn pty_resize(&mut self, pane_id: &str, cols: u16, rows: u16) -> Result<(), NexusError> {
        self.request("pty.resize", serde_json::json!({
            "pane_id": pane_id, "cols": cols, "rows": rows
        }))?;
        Ok(())
    }

    pub fn pty_kill(&mut self, pane_id: &str) -> Result<(), NexusError> {
        self.request("pty.kill", serde_json::json!({"pane_id": pane_id}))?;
        Ok(())
    }

    pub fn chat_send(&mut self, pane_id: &str, message: &str, cwd: Option<&str>) -> Result<(), NexusError> {
        let mut params = serde_json::json!({"pane_id": pane_id, "message": message});
        if let Some(cwd) = cwd {
            params["cwd"] = serde_json::json!(cwd);
        }
        self.request("chat.send", params)?;
        Ok(())
    }

    pub fn stack_op(&mut self, op: &str, payload: &HashMap<String, String>) -> Result<serde_json::Value, NexusError> {
        let params: serde_json::Value = payload.iter()
            .map(|(k, v)| (k.clone(), serde_json::Value::String(v.clone())))
            .collect::<serde_json::Map<String, serde_json::Value>>()
            .into();
        self.request(&format!("stack.{op}"), params)
    }

    pub fn layout(&mut self) -> Result<serde_json::Value, NexusError> {
        self.request("layout.show", serde_json::Value::Null)
    }

    pub fn keymap(&mut self) -> Result<serde_json::Value, NexusError> {
        self.request("keymap.get", serde_json::Value::Null)
    }

    pub fn commands(&mut self) -> Result<serde_json::Value, NexusError> {
        self.request("commands.list", serde_json::Value::Null)
    }

    pub fn capabilities(&mut self, cap_type: Option<&str>) -> Result<serde_json::Value, NexusError> {
        let params = match cap_type {
            Some(t) => serde_json::json!({"type": t}),
            None => serde_json::Value::Null,
        };
        self.request("capabilities.list", params)
    }

    pub fn hello(&mut self) -> Result<serde_json::Value, NexusError> {
        self.request("nexus.hello", serde_json::Value::Null)
    }

    pub fn session_info(&mut self) -> Result<serde_json::Value, NexusError> {
        self.request("session.info", serde_json::Value::Null)
    }

    pub fn session_create(&mut self, name: &str, cwd: &str) -> Result<serde_json::Value, NexusError> {
        self.request("session.create", serde_json::json!({"name": name, "cwd": cwd}))
    }

    pub fn close_pane(&mut self, pane_id: &str) -> Result<serde_json::Value, NexusError> {
        self.request("pane.close", serde_json::json!({"pane_id": pane_id}))
    }

    pub fn zoom(&mut self) -> Result<serde_json::Value, NexusError> {
        self.request("pane.zoom", serde_json::Value::Null)
    }

    pub fn focus(&mut self, pane_id: &str) -> Result<serde_json::Value, NexusError> {
        self.request("pane.focus", serde_json::json!({"pane_id": pane_id}))
    }

    pub fn resize(&mut self, pane_id: &str, ratio: f64) -> Result<serde_json::Value, NexusError> {
        self.request("pane.resize", serde_json::json!({"pane_id": pane_id, "ratio": ratio}))
    }
}
```

- [ ] **Step 3: Implement EventSubscription**

`crates/nexus-client/src/events.rs`:
```rust
//! EventSubscription — synchronous filtered event stream from the daemon.

use crate::protocol::{JsonRpcNotification, JsonRpcRequest, JsonRpcResponse};
use nexus_core::NexusError;
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixStream;
use std::sync::atomic::{AtomicU64, Ordering};

/// A connection to the daemon's event socket with active subscription.
pub struct EventSubscription {
    reader: BufReader<UnixStream>,
    writer: UnixStream,
    next_id: AtomicU64,
}

impl EventSubscription {
    /// Connect to the event socket and subscribe to the given patterns.
    pub fn subscribe(
        patterns: &[&str],
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<Self, NexusError> {
        let path = nexus_core::constants::events_socket_path();
        Self::subscribe_to(
            path.to_str().unwrap_or(""),
            patterns,
            filter,
        )
    }

    /// Connect to a specific event socket path (for testing).
    pub fn subscribe_to(
        path: &str,
        patterns: &[&str],
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<Self, NexusError> {
        let stream = UnixStream::connect(path)
            .map_err(|e| NexusError::Protocol(format!("event connect: {e}")))?;
        let reader = BufReader::new(stream.try_clone()
            .map_err(|e| NexusError::Protocol(format!("clone: {e}")))?);
        let mut sub = Self {
            reader,
            writer: stream,
            next_id: AtomicU64::new(1),
        };
        sub.send_subscribe(patterns, filter)?;
        Ok(sub)
    }

    /// Update the subscription (replaces current patterns/filter).
    pub fn resubscribe(
        &mut self,
        patterns: &[&str],
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<(), NexusError> {
        self.send_subscribe(patterns, filter)
    }

    /// Block until the next event arrives.
    pub fn next_event(&mut self) -> Result<JsonRpcNotification, NexusError> {
        let mut buf = String::new();
        self.reader.read_line(&mut buf)
            .map_err(|e| NexusError::Protocol(format!("read event: {e}")))?;
        if buf.is_empty() {
            return Err(NexusError::Protocol("event connection closed".into()));
        }
        serde_json::from_str(&buf)
            .map_err(|e| NexusError::Protocol(format!("parse event: {e}")))?
    }

    fn send_subscribe(
        &mut self,
        patterns: &[&str],
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<(), NexusError> {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed);
        let mut params = serde_json::json!({"patterns": patterns});
        if let Some(f) = filter {
            params["filter"] = serde_json::to_value(f)
                .map_err(|e| NexusError::Protocol(e.to_string()))?;
        }
        let req = JsonRpcRequest::new(id, "subscribe", params);
        let mut line = serde_json::to_string(&req)
            .map_err(|e| NexusError::Protocol(e.to_string()))?;
        line.push('\n');
        self.writer.write_all(line.as_bytes())
            .map_err(|e| NexusError::Protocol(format!("write subscribe: {e}")))?;

        // Read acknowledgment
        let mut buf = String::new();
        self.reader.read_line(&mut buf)
            .map_err(|e| NexusError::Protocol(format!("read ack: {e}")))?;
        let resp: JsonRpcResponse = serde_json::from_str(&buf)
            .map_err(|e| NexusError::Protocol(format!("parse ack: {e}")))?;
        if let Some(err) = resp.error {
            return Err(NexusError::Protocol(err.message));
        }
        Ok(())
    }
}
```

- [ ] **Step 4: Update lib.rs to expose all modules**

```rust
//! Nexus client library — sync JSON-RPC 2.0 client for the Nexus daemon.
//!
//! Provides `NexusClient` (command connection) and `EventSubscription`
//! (filtered event stream). Surfaces (CLI, Tauri, tmux) depend on this
//! crate — never on the engine directly.

pub mod auto_launch;
pub mod client;
pub mod events;
pub mod protocol;

pub use client::NexusClient;
pub use events::EventSubscription;
pub use protocol::{JsonRpcError, JsonRpcNotification, JsonRpcRequest, JsonRpcResponse};
```

- [ ] **Step 5: Run tests (protocol tests still pass, new code compiles)**

Run: `cd crates && cargo test -p nexus-client`
Expected: Protocol tests pass, new modules compile.

- [ ] **Step 6: Commit**

```bash
git add crates/nexus-client/
git commit -m "feat(client): add NexusClient, EventSubscription, and auto-launch"
```

---

### Task 6: nexus-daemon — event bridge

Create the mpsc-based bridge that decouples EventBus (sync) from async event connections.

**Files:**
- Create: `crates/nexus-daemon/src/event_bridge.rs`
- Modify: `crates/nexus-daemon/src/lib.rs`

- [ ] **Step 1: Implement event bridge**

`crates/nexus-daemon/src/event_bridge.rs`:
```rust
//! Event bridge — mpsc channel between sync EventBus and async event connections.
//!
//! The EventBus fires callbacks synchronously while holding its mutex.
//! This bridge uses an mpsc::unbounded_channel to decouple the EventBus
//! from async socket writes.

use nexus_engine::TypedEvent;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::io::AsyncWriteExt;
use tokio::net::unix::OwnedWriteHalf;
use tokio::sync::Mutex;

/// Subscription filter — pattern + key-value matching, testable without a socket.
#[derive(Debug, Clone)]
pub struct SubscriptionFilter {
    pub patterns: Vec<String>,
    pub filter: HashMap<String, serde_json::Value>,
}

impl SubscriptionFilter {
    /// Check if an event matches this subscription.
    pub fn matches(&self, event: &TypedEvent) -> bool {
        // Check pattern match
        let source = &event.source;
        let pattern_match = self.patterns.iter().any(|p| {
            if p == "*.*" || p == "*" {
                return true;
            }
            if p.ends_with(".*") {
                let prefix = &p[..p.len() - 2];
                return source.starts_with(prefix) && source[prefix.len()..].starts_with('.');
            }
            p == source
        });

        if !pattern_match {
            return false;
        }

        // Check filter match (all filter keys must match event payload)
        for (key, expected) in &self.filter {
            match event.payload.get(key) {
                Some(actual) => {
                    if actual != expected {
                        return false;
                    }
                }
                None => return false,
            }
        }

        true
    }
}

/// Active event connection with subscription filters.
pub struct EventConnection {
    pub writer: OwnedWriteHalf,
    pub sub: SubscriptionFilter,
}

impl EventConnection {
    /// Write a JSON-RPC notification to this connection.
    pub async fn write_event(&mut self, event: &TypedEvent) -> bool {
        let notif = nexus_client::JsonRpcNotification::new(
            &event.source,
            serde_json::Value::Object(
                event.payload.iter()
                    .map(|(k, v)| (k.clone(), v.clone()))
                    .collect(),
            ),
        );

        let mut line = match serde_json::to_string(&notif) {
            Ok(s) => s,
            Err(_) => return false,
        };
        line.push('\n');

        self.writer.write_all(line.as_bytes()).await.is_ok()
    }
}

/// Shared state for all event connections.
pub type SharedConnections = Arc<Mutex<Vec<EventConnection>>>;

/// Spawn the event fan-out task.
///
/// Reads events from the mpsc channel and writes to all matching connections.
/// Removes connections that fail to write (disconnected).
pub fn spawn_fanout(
    mut rx: tokio::sync::mpsc::UnboundedReceiver<TypedEvent>,
    connections: SharedConnections,
) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        while let Some(event) = rx.recv().await {
            let mut conns = connections.lock().await;
            let mut to_remove = Vec::new();

            for (i, conn) in conns.iter_mut().enumerate() {
                if conn.sub.matches(&event) {
                    if !conn.write_event(&event).await {
                        to_remove.push(i);
                    }
                }
            }

            // Remove disconnected (in reverse order to preserve indices)
            for i in to_remove.into_iter().rev() {
                conns.swap_remove(i);
            }
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use nexus_engine::{EventType, TypedEvent};

    fn make_event(source: &str, payload: &[(&str, &str)]) -> TypedEvent {
        let mut event = TypedEvent::new(EventType::Custom, source);
        for (k, v) in payload {
            event = event.with_payload(*k, *v);
        }
        event
    }

    fn make_filter(patterns: &[&str], filter: &[(&str, &str)]) -> SubscriptionFilter {
        SubscriptionFilter {
            patterns: patterns.iter().map(|s| s.to_string()).collect(),
            filter: filter.iter().map(|(k, v)| (k.to_string(), serde_json::json!(v))).collect(),
        }
    }

    #[test]
    fn exact_pattern_matches() {
        let sub = make_filter(&["pty.output"], &[]);
        let event = make_event("pty.output", &[("pane_id", "p1")]);
        assert!(sub.matches(&event));
    }

    #[test]
    fn wildcard_pattern_matches() {
        let sub = make_filter(&["pty.*"], &[]);
        assert!(sub.matches(&make_event("pty.output", &[])));
        assert!(sub.matches(&make_event("pty.exit", &[])));
        assert!(!sub.matches(&make_event("agent.text", &[])));
    }

    #[test]
    fn star_star_matches_everything() {
        let sub = make_filter(&["*.*"], &[]);
        assert!(sub.matches(&make_event("pty.output", &[])));
        assert!(sub.matches(&make_event("agent.done", &[])));
    }

    #[test]
    fn filter_restricts_by_payload() {
        let sub = make_filter(&["pty.*"], &[("pane_id", "p1")]);
        assert!(sub.matches(&make_event("pty.output", &[("pane_id", "p1")])));
        assert!(!sub.matches(&make_event("pty.output", &[("pane_id", "p2")])));
    }

    #[test]
    fn filter_missing_key_no_match() {
        let sub = make_filter(&["pty.*"], &[("pane_id", "p1")]);
        assert!(!sub.matches(&make_event("pty.output", &[])));
    }
}
```

- [ ] **Step 2: Update lib.rs**

Add the new module to `crates/nexus-daemon/src/lib.rs` (keep existing modules until Task 7 deletes them):
```rust
pub mod client;
pub mod event_bridge;
pub mod protocol;
pub mod server;
```

- [ ] **Step 3: Update Cargo.toml**

Add `nexus-client` dependency to `crates/nexus-daemon/Cargo.toml`:

```toml
[dependencies]
nexus-core = { path = "../nexus-core" }
nexus-engine = { path = "../nexus-engine" }
nexus-client = { path = "../nexus-client" }
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

- [ ] **Step 4: Run tests**

Run: `cd crates && cargo test -p nexus-daemon -- event_bridge`
Expected: All matching tests pass (note: the `unsafe { std::mem::zeroed() }` for writer is only used in pattern matching tests, not write tests).

- [ ] **Step 5: Commit**

```bash
git add crates/nexus-daemon/
git commit -m "feat(daemon): add event bridge with mpsc fan-out and pattern/filter matching"
```

---

### Task 7: nexus-daemon — server rewrite

Rewrite the daemon server with two listeners, spawn_blocking, all routing through dispatch(). Delete old protocol.rs and client.rs.

**Files:**
- Delete: `crates/nexus-daemon/src/protocol.rs`
- Delete: `crates/nexus-daemon/src/client.rs`
- Rewrite: `crates/nexus-daemon/src/server.rs`
- Rewrite: `crates/nexus-daemon/src/main.rs`
- Modify: `crates/nexus-daemon/src/lib.rs`

- [ ] **Step 1: Delete old files**

```bash
rm crates/nexus-daemon/src/protocol.rs crates/nexus-daemon/src/client.rs
```

- [ ] **Step 2: Update lib.rs**

`crates/nexus-daemon/src/lib.rs`:
```rust
pub mod event_bridge;
pub mod server;
```

- [ ] **Step 3: Rewrite server.rs**

`crates/nexus-daemon/src/server.rs`:
```rust
//! Daemon server — two Unix socket listeners, JSON-RPC 2.0, all through dispatch().

use crate::event_bridge::{EventConnection, SharedConnections};
use nexus_client::{JsonRpcRequest, JsonRpcResponse};
use nexus_engine::NexusCore;
use std::collections::HashMap;
use std::sync::{Arc, Mutex as StdMutex};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixListener;
use tokio::sync::watch;

/// Shared engine state (std::sync::Mutex, NOT tokio).
pub type SharedCore = Arc<StdMutex<NexusCore>>;

/// Connected client counter for idle shutdown.
pub type ClientCount = Arc<std::sync::atomic::AtomicUsize>;

/// Run the command socket accept loop.
pub async fn run_command_listener(
    listener: UnixListener,
    core: SharedCore,
    client_count: ClientCount,
    mut shutdown: watch::Receiver<bool>,
) {
    loop {
        tokio::select! {
            result = listener.accept() => {
                match result {
                    Ok((stream, _)) => {
                        client_count.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                        let core = core.clone();
                        let count = client_count.clone();
                        tokio::spawn(async move {
                            handle_command_connection(stream, core).await;
                            count.fetch_sub(1, std::sync::atomic::Ordering::Relaxed);
                        });
                    }
                    Err(e) => eprintln!("command accept error: {e}"),
                }
            }
            _ = shutdown.changed() => {
                break;
            }
        }
    }
}

/// Run the event socket accept loop.
pub async fn run_event_listener(
    listener: UnixListener,
    connections: SharedConnections,
    mut shutdown: watch::Receiver<bool>,
) {
    loop {
        tokio::select! {
            result = listener.accept() => {
                match result {
                    Ok((stream, _)) => {
                        let conns = connections.clone();
                        tokio::spawn(async move {
                            handle_event_connection(stream, conns).await;
                        });
                    }
                    Err(e) => eprintln!("event accept error: {e}"),
                }
            }
            _ = shutdown.changed() => {
                break;
            }
        }
    }
}

async fn handle_command_connection(
    stream: tokio::net::UnixStream,
    core: SharedCore,
) {
    let (reader, mut writer) = stream.into_split();
    let mut lines = BufReader::new(reader).lines();

    while let Ok(Some(line)) = lines.next_line().await {
        let response = match serde_json::from_str::<JsonRpcRequest>(&line) {
            Ok(req) => {
                let core = core.clone();
                let method = req.method.clone();
                let params = req.params.clone();
                let id = req.id;

                // Convert params Value to HashMap for dispatch
                let args: HashMap<String, serde_json::Value> = match &params {
                    serde_json::Value::Object(map) => {
                        map.iter().map(|(k, v)| (k.clone(), v.clone())).collect()
                    }
                    _ => HashMap::new(),
                };

                // spawn_blocking to avoid blocking tokio runtime
                match tokio::task::spawn_blocking(move || {
                    let mut core = core.lock().unwrap();
                    nexus_engine::dispatch(&mut core, &method, &args)
                }).await {
                    Ok(Ok(result)) => JsonRpcResponse::success(id, result),
                    Ok(Err(e)) => JsonRpcResponse::error(id, -1, &e.to_string()),
                    Err(e) => JsonRpcResponse::error(id, -2, &format!("internal: {e}")),
                }
            }
            Err(e) => JsonRpcResponse::error(0, -32700, &format!("parse error: {e}")),
        };

        let mut out = match serde_json::to_string(&response) {
            Ok(s) => s,
            Err(_) => r#"{"jsonrpc":"2.0","id":0,"error":{"code":-32603,"message":"serialize failed"}}"#.into(),
        };
        out.push('\n');

        if writer.write_all(out.as_bytes()).await.is_err() {
            break;
        }
    }
}

async fn handle_event_connection(
    stream: tokio::net::UnixStream,
    connections: SharedConnections,
) {
    let (reader, writer) = stream.into_split();
    let mut lines = BufReader::new(reader).lines();

    // Read subscribe requests
    while let Ok(Some(line)) = lines.next_line().await {
        let req: JsonRpcRequest = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(_) => continue,
        };

        if req.method != "subscribe" {
            continue;
        }

        let patterns: Vec<String> = req.params.get("patterns")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();

        let filter: HashMap<String, serde_json::Value> = req.params.get("filter")
            .and_then(|v| v.as_object())
            .map(|m| m.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
            .unwrap_or_default();

        // Remove any existing connection with this writer (resubscribe)
        // For simplicity, we add a new one each time. The fan-out task
        // will clean up dead connections.

        // Send ack
        let ack = JsonRpcResponse::success(req.id, serde_json::json!({
            "patterns": patterns,
            "filter": filter,
        }));
        let mut ack_line = serde_json::to_string(&ack).unwrap_or_default();
        ack_line.push('\n');

        // We need the writer to send the ack, then hand it to the connection list.
        // Since we only get one writer, handle the first subscribe and then
        // keep reading for resubscribes.

        let conn = EventConnection {
            writer,
            sub: SubscriptionFilter { patterns, filter },
        };

        // Write ack through the connection's writer before registering
        // (need mutable access)
        let mut conns = connections.lock().await;
        conns.push(conn);
        let last = conns.last_mut().unwrap();
        let _ = last.writer.write_all(ack_line.as_bytes()).await;
        drop(conns);

        // v1 LIMITATION: writer is moved into EventConnection on first subscribe.
        // Resubscription requires client to disconnect and reconnect with new patterns.
        // Future: use an Arc<Mutex<SubscriptionFilter>> to allow in-place updates.
        break;
    }

    // Connection stays alive in the connections list until fan-out detects disconnect.
}

/// Check idle conditions and trigger shutdown if idle for 30s.
pub async fn idle_shutdown_monitor(
    core: SharedCore,
    client_count: ClientCount,
    shutdown_tx: watch::Sender<bool>,
) {
    let mut idle_seconds = 0u32;

    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;

        let clients = client_count.load(std::sync::atomic::Ordering::Relaxed);
        let ptys = {
            let core = core.lock().unwrap();
            core.active_pty_count()
        };

        if clients == 0 && ptys == 0 {
            idle_seconds += 5;
            if idle_seconds >= 30 {
                eprintln!("Idle for 30s with no clients and no PTYs — shutting down");
                let _ = shutdown_tx.send(true);
                return;
            }
        } else {
            idle_seconds = 0;
        }
    }
}
```

- [ ] **Step 4: Rewrite main.rs**

`crates/nexus-daemon/src/main.rs`:
```rust
//! Nexus daemon — shared NexusCore over unix socket.
//!
//! Owns the engine. All surfaces connect here as JSON-RPC 2.0 clients.

use nexus_core::adapters::{ClaudeAdapter, FsExplorer};
use nexus_core::capability::SystemContext;
use nexus_engine::{NexusCore, NullMux, TypedEvent};
use std::sync::{Arc, Mutex as StdMutex};

#[tokio::main]
async fn main() {
    // -- Arg handling --
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("nexus-daemon — shared NexusCore over unix socket");
        println!();
        println!("Usage: nexus-daemon [--socket PATH]");
        println!();
        println!("Options:");
        println!("  --socket PATH    Command socket path override");
        println!("  -h, --help       Print this help");
        return;
    }

    let cmd_socket = args
        .windows(2)
        .find(|w| w[0] == "--socket")
        .map(|w| std::path::PathBuf::from(&w[1]))
        .unwrap_or_else(nexus_core::constants::socket_path);

    let event_socket = {
        let mut p = cmd_socket.clone();
        p.set_file_name("nexus-events.sock");
        p
    };

    let pid_file = {
        let mut p = cmd_socket.clone();
        p.set_file_name("nexus.pid");
        p
    };

    // -- Directory setup --
    if let Some(parent) = cmd_socket.parent() {
        if let Err(e) = std::fs::create_dir_all(parent) {
            eprintln!("Cannot create socket directory {}: {e}", parent.display());
            std::process::exit(1);
        }
    }

    // Remove stale sockets
    let _ = std::fs::remove_file(&cmd_socket);
    let _ = std::fs::remove_file(&event_socket);

    // Write PID file
    if let Err(e) = std::fs::write(&pid_file, std::process::id().to_string()) {
        eprintln!("Warning: could not write PID file: {e}");
    }

    // -- Bind listeners --
    let cmd_listener = match tokio::net::UnixListener::bind(&cmd_socket) {
        Ok(l) => l,
        Err(e) => {
            eprintln!("Cannot bind command socket {}: {e}", cmd_socket.display());
            std::process::exit(1);
        }
    };

    let event_listener = match tokio::net::UnixListener::bind(&event_socket) {
        Ok(l) => l,
        Err(e) => {
            eprintln!("Cannot bind event socket {}: {e}", event_socket.display());
            std::process::exit(1);
        }
    };

    eprintln!("nexus-daemon listening:");
    eprintln!("  commands: {}", cmd_socket.display());
    eprintln!("  events:   {}", event_socket.display());
    eprintln!("  PID:      {}", std::process::id());

    // -- Initialize engine --
    let ctx = SystemContext::from_login_shell();
    let claude = ClaudeAdapter::new(ctx.clone());
    let fs_explorer = FsExplorer::new();

    let cwd = std::env::current_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| "/tmp".into());

    let mut core = NexusCore::with_registry(Box::new(NullMux::new()), ctx);
    if let Some(ref mut reg) = core.registry {
        reg.register_chat(Box::new(claude));
        reg.register_explorer(Box::new(fs_explorer));
    }
    core.create_workspace("nexus", &cwd);

    // -- Event bridge --
    let (event_tx, event_rx) = tokio::sync::mpsc::unbounded_channel::<TypedEvent>();
    {
        let mut bus = core.bus.lock().unwrap();
        bus.subscribe("*.*", move |event| {
            let _ = event_tx.send(event.clone());
        });
    }

    let connections = nexus_daemon::event_bridge::SharedConnections::default();
    let _fanout = nexus_daemon::event_bridge::spawn_fanout(event_rx, connections.clone());

    // -- Shared state --
    let core = Arc::new(StdMutex::new(core));
    let client_count = nexus_daemon::server::ClientCount::default();

    // -- Shutdown channel --
    let (shutdown_tx, shutdown_rx) = tokio::sync::watch::channel(false);

    // -- Run --
    let cmd_socket_path = cmd_socket.clone();
    let event_socket_path = event_socket.clone();
    let pid_path = pid_file.clone();

    tokio::select! {
        _ = nexus_daemon::server::run_command_listener(
            cmd_listener, core.clone(), client_count.clone(), shutdown_rx.clone()
        ) => {}
        _ = nexus_daemon::server::run_event_listener(
            event_listener, connections, shutdown_rx.clone()
        ) => {}
        _ = nexus_daemon::server::idle_shutdown_monitor(
            core.clone(), client_count, shutdown_tx
        ) => {}
        _ = tokio::signal::ctrl_c() => {
            eprintln!("\nShutting down...");
        }
    }

    // -- Cleanup --
    let _ = std::fs::remove_file(&cmd_socket_path);
    let _ = std::fs::remove_file(&event_socket_path);
    let _ = std::fs::remove_file(&pid_path);
    eprintln!("Cleaned up socket and PID files");
}
```

- [ ] **Step 5: Verify compilation**

Run: `cd crates && cargo build -p nexus-daemon`
Expected: Compiles successfully.

- [ ] **Step 6: Commit**

```bash
git add crates/nexus-daemon/
git commit -m "feat(daemon): rewrite server with dual sockets, spawn_blocking, dispatch routing, idle shutdown"
```

---

## Phase 3: Thin Clients (Tasks 8-10)

Convert surfaces to thin clients using nexus-client.

---

### Task 8: nexus-cli — thin client rewrite

Replace in-process NexusCore with NexusClient. Keep clap subcommands, delegate to `client.request()`.

**Files:**
- Modify: `crates/nexus-cli/Cargo.toml`
- Rewrite: `crates/nexus-cli/src/main.rs`

- [ ] **Step 1: Update Cargo.toml**

Replace `nexus-engine` dep with `nexus-client` and `nexus-core`:

```toml
[package]
name = "nexus-cli"
version = "0.1.0"
edition = "2021"
description = "Nexus Shell CLI — thin client for the Nexus daemon"

[dependencies]
nexus-client = { path = "../nexus-client" }
nexus-core = { path = "../nexus-core" }
clap = { version = "4", features = ["derive"] }
serde_json = "1"

[[bin]]
name = "nexus"
path = "src/main.rs"
```

- [ ] **Step 2: Rewrite main.rs**

`crates/nexus-cli/src/main.rs`:
```rust
//! Nexus CLI — thin client for the Nexus daemon.
//!
//! Every subcommand connects to the daemon via NexusClient and sends
//! a single JSON-RPC request. The daemon owns the engine.

use clap::{Parser, Subcommand};
use nexus_client::NexusClient;
use std::collections::HashMap;

#[derive(Parser)]
#[command(name = "nexus", about = "Nexus Shell CLI")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Stack operations (push, switch, close, list, tag, rename)
    Stack {
        #[command(subcommand)]
        action: StackAction,
    },
    /// Layout operations (show, split, navigate, focus, zoom)
    Layout {
        #[command(subcommand)]
        action: LayoutAction,
    },
    /// Session operations
    Session {
        #[command(subcommand)]
        action: SessionAction,
    },
    /// Pane operations
    Pane {
        #[command(subcommand)]
        action: PaneAction,
    },
    /// Show daemon info
    Hello,
}

#[derive(Subcommand)]
enum StackAction {
    Push {
        #[arg(short, long)]
        identity: String,
        #[arg(short, long)]
        pane_id: String,
        #[arg(short, long, default_value = "Shell")]
        name: String,
    },
    Switch {
        #[arg(short, long)]
        identity: String,
        #[arg(short = 'x', long)]
        index: usize,
    },
    Close {
        #[arg(short, long)]
        identity: String,
    },
    Tag {
        #[arg(short, long)]
        identity: String,
        #[arg(short, long)]
        tag: String,
    },
    Rename {
        #[arg(short, long)]
        identity: String,
        #[arg(short, long)]
        name: String,
    },
}

#[derive(Subcommand)]
enum LayoutAction {
    Show,
    Split {
        #[arg(short, long, default_value = "vertical")]
        direction: String,
        #[arg(short, long, default_value = "terminal")]
        pane_type: String,
    },
    Navigate { direction: String },
    Focus { pane_id: String },
    Zoom,
}

#[derive(Subcommand)]
enum SessionAction {
    Create {
        #[arg(short, long, default_value = "nexus")]
        name: String,
        #[arg(short, long)]
        cwd: Option<String>,
    },
    Info,
    List,
}

#[derive(Subcommand)]
enum PaneAction {
    List,
    Close {
        #[arg(short, long)]
        pane_id: String,
    },
}

fn main() {
    let cli = Cli::parse();

    let mut client = match NexusClient::connect() {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Failed to connect to daemon: {e}");
            std::process::exit(1);
        }
    };

    let result = match cli.command {
        Commands::Stack { action } => handle_stack(&mut client, action),
        Commands::Layout { action } => handle_layout(&mut client, action),
        Commands::Session { action } => handle_session(&mut client, action),
        Commands::Pane { action } => handle_pane(&mut client, action),
        Commands::Hello => client.hello(),
    };

    match result {
        Ok(val) => {
            if !val.is_null() {
                println!("{}", serde_json::to_string_pretty(&val).unwrap_or_default());
            } else {
                println!("ok");
            }
        }
        Err(e) => {
            eprintln!("error: {e}");
            std::process::exit(1);
        }
    }
}

fn handle_stack(client: &mut NexusClient, action: StackAction) -> Result<serde_json::Value, nexus_core::NexusError> {
    match action {
        StackAction::Push { identity, pane_id, name } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
                ("pane_id".into(), pane_id),
                ("name".into(), name),
            ].into_iter().collect();
            client.stack_op("push", &payload)
        }
        StackAction::Switch { identity, index } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
                ("index".into(), index.to_string()),
            ].into_iter().collect();
            client.stack_op("switch", &payload)
        }
        StackAction::Close { identity } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
            ].into_iter().collect();
            client.stack_op("close", &payload)
        }
        StackAction::Tag { identity, tag } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
                ("tag".into(), tag),
            ].into_iter().collect();
            client.stack_op("tag", &payload)
        }
        StackAction::Rename { identity, name } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
                ("name".into(), name),
            ].into_iter().collect();
            client.stack_op("rename", &payload)
        }
    }
}

fn handle_layout(client: &mut NexusClient, action: LayoutAction) -> Result<serde_json::Value, nexus_core::NexusError> {
    match action {
        LayoutAction::Show => client.layout(),
        LayoutAction::Split { direction, pane_type } => {
            client.request("pane.split", serde_json::json!({
                "direction": direction,
                "pane_type": pane_type,
            }))
        }
        LayoutAction::Navigate { direction } => client.navigate(&direction),
        LayoutAction::Focus { pane_id } => client.focus(&pane_id),
        LayoutAction::Zoom => client.zoom(),
    }
}

fn handle_session(client: &mut NexusClient, action: SessionAction) -> Result<serde_json::Value, nexus_core::NexusError> {
    let cwd = std::env::current_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| "/tmp".into());

    match action {
        SessionAction::Create { name, cwd: explicit_cwd } => {
            let dir = explicit_cwd.as_deref().unwrap_or(&cwd);
            client.session_create(&name, dir)
        }
        SessionAction::Info => client.session_info(),
        SessionAction::List => client.request("session.list", serde_json::Value::Null),
    }
}

fn handle_pane(client: &mut NexusClient, action: PaneAction) -> Result<serde_json::Value, nexus_core::NexusError> {
    match action {
        PaneAction::List => client.pane_list(),
        PaneAction::Close { pane_id } => client.close_pane(&pane_id),
    }
}
```

- [ ] **Step 3: Verify compilation**

Run: `cd crates && cargo build -p nexus-cli`
Expected: Compiles. Binary is now a thin client.

- [ ] **Step 4: Commit**

```bash
git add crates/nexus-cli/
git commit -m "feat(cli): rewrite as thin client using NexusClient"
```

---

### Task 9: nexus-tauri — thin client rewrite

Replace embedded NexusCore with NexusClient. Event subscription replaces direct EventBus access.

**Files:**
- Modify: `crates/nexus-tauri/Cargo.toml`
- Rewrite: `crates/nexus-tauri/src/main.rs`
- Rewrite: `crates/nexus-tauri/src/commands.rs`

- [ ] **Step 1: Update Cargo.toml**

Replace `nexus-engine` with `nexus-client`:

```toml
[package]
name = "nexus-tauri"
version = "0.1.0"
edition = "2021"
description = "Nexus Shell desktop app — Tauri surface (thin client)"

[dependencies]
nexus-core = { path = "../nexus-core" }
nexus-client = { path = "../nexus-client" }
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[[bin]]
name = "nexus-tauri"
path = "src/main.rs"
```

- [ ] **Step 2: Rewrite main.rs**

`crates/nexus-tauri/src/main.rs`:
```rust
//! Nexus Shell — Tauri desktop app (thin client).
//!
//! Connects to nexus-daemon via NexusClient. All engine state lives in
//! the daemon. This binary is a pure GUI frontend.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;

use nexus_client::{EventSubscription, NexusClient};
use std::sync::Mutex;
use tauri::Manager;

/// Shared application state — holds the daemon client connection.
pub struct AppState {
    pub client: Mutex<NexusClient>,
}

fn main() {
    let client = NexusClient::connect().expect("Failed to connect to nexus daemon");

    tauri::Builder::default()
        .manage(AppState {
            client: Mutex::new(client),
        })
        .invoke_handler(tauri::generate_handler![
            commands::create_workspace,
            commands::stack_op,
            commands::list_tabs,
            commands::get_session,
            commands::read_dir,
            commands::read_file,
            commands::get_cwd,
            commands::get_layout,
            commands::split_pane,
            commands::navigate_pane,
            commands::focus_pane,
            commands::close_pane,
            commands::zoom_pane,
            commands::resize_pane,
            commands::pty_spawn,
            commands::pty_write,
            commands::pty_resize,
            commands::pty_kill,
            commands::agent_send,
            commands::get_keymap,
            commands::get_commands,
            commands::dispatch_command,
        ])
        .setup(|app| {
            // Bridge daemon events to Tauri frontend via EventSubscription
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                // Subscribe to all events
                let mut sub = match EventSubscription::subscribe(&["*.*"], None) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Event subscription failed: {e}");
                        return;
                    }
                };

                loop {
                    match sub.next_event() {
                        Ok(notif) => {
                            use tauri::Emitter;
                            let tauri_event = match notif.method.as_str() {
                                "pty.output" => "pty-output",
                                "pty.exit" => "pty-exit",
                                s if s.starts_with("agent.") => "agent-output",
                                "layout.changed" => "layout-changed",
                                "stack.changed" => "stack-changed",
                                _ => continue,
                            };

                            let mut payload = match notif.params.as_object() {
                                Some(m) => m.clone(),
                                None => serde_json::Map::new(),
                            };

                            // For agent events, add the type field
                            if notif.method.starts_with("agent.") {
                                let event_type = notif.method.strip_prefix("agent.").unwrap_or("");
                                payload.insert("type".into(), serde_json::json!(event_type));
                            }

                            let _ = app_handle.emit(tauri_event, &serde_json::Value::Object(payload));
                        }
                        Err(_) => {
                            // Connection lost — try to reconnect
                            std::thread::sleep(std::time::Duration::from_secs(1));
                            sub = match EventSubscription::subscribe(&["*.*"], None) {
                                Ok(s) => s,
                                Err(_) => continue,
                            };
                        }
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error running Nexus Shell");
}
```

- [ ] **Step 3: Rewrite commands.rs**

`crates/nexus-tauri/src/commands.rs`:
```rust
//! Tauri commands — IPC bridge between frontend and nexus-daemon.
//!
//! Each command locks the NexusClient and sends a JSON-RPC request.

use crate::AppState;
use serde::Serialize;
use std::collections::HashMap;
use std::path::PathBuf;
use tauri::State;

// -- Engine commands (delegated to daemon) -----------------------------------

#[tauri::command]
pub fn create_workspace(
    state: State<AppState>,
    name: String,
    cwd: String,
) -> Result<String, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    let result = client.session_create(&name, &cwd).map_err(|e| e.to_string())?;
    Ok(result.get("session_id").and_then(|v| v.as_str()).unwrap_or("").to_string())
}

#[tauri::command]
pub fn stack_op(
    state: State<AppState>,
    op: String,
    payload: HashMap<String, String>,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.stack_op(&op, &payload).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn list_tabs(
    state: State<AppState>,
    identity: String,
) -> Result<Vec<serde_json::Value>, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    let result = client.request(
        "stack.list",
        serde_json::json!({"identity": identity}),
    ).map_err(|e| e.to_string())?;
    match result.as_array() {
        Some(arr) => Ok(arr.clone()),
        None => Ok(Vec::new()),
    }
}

#[tauri::command]
pub fn get_session(state: State<AppState>) -> Result<Option<String>, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    let result = client.session_info().map_err(|e| e.to_string())?;
    Ok(result.get("name").and_then(|v| v.as_str()).map(String::from))
}

// -- Filesystem commands (local, not through daemon) -------------------------

#[derive(Serialize)]
pub struct DirEntry {
    name: String,
    path: String,
    is_dir: bool,
}

#[tauri::command]
pub fn read_dir(path: String) -> Result<Vec<DirEntry>, String> {
    let dir = PathBuf::from(&path);
    if !dir.is_dir() {
        return Err(format!("Not a directory: {path}"));
    }

    let mut entries: Vec<DirEntry> = std::fs::read_dir(&dir)
        .map_err(|e| e.to_string())?
        .filter_map(|e| e.ok())
        .filter(|e| {
            let name = e.file_name().to_string_lossy().to_string();
            !name.starts_with('.') && name != "target" && name != "node_modules"
                && name != "__pycache__"
        })
        .map(|e| {
            let is_dir = e.file_type().map(|t| t.is_dir()).unwrap_or(false);
            DirEntry {
                name: e.file_name().to_string_lossy().to_string(),
                path: e.path().to_string_lossy().to_string(),
                is_dir,
            }
        })
        .collect();

    entries.sort_by(|a, b| {
        b.is_dir.cmp(&a.is_dir).then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
    });

    Ok(entries)
}

#[tauri::command]
pub fn read_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(&path).map_err(|e| format!("{path}: {e}"))
}

#[tauri::command]
pub fn get_cwd() -> Result<String, String> {
    std::env::current_dir()
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|e| e.to_string())
}

// -- Layout commands ---------------------------------------------------------

#[tauri::command]
pub fn get_layout(state: State<AppState>) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.layout().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn split_pane(
    state: State<AppState>,
    direction: String,
    pane_type: String,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.request("pane.split", serde_json::json!({
        "direction": direction,
        "pane_type": pane_type,
    })).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn navigate_pane(
    state: State<AppState>,
    direction: String,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.navigate(&direction).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn focus_pane(
    state: State<AppState>,
    pane_id: String,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.focus(&pane_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn close_pane(
    state: State<AppState>,
    pane_id: String,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.close_pane(&pane_id).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn zoom_pane(state: State<AppState>) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.zoom().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn resize_pane(
    state: State<AppState>,
    pane_id: String,
    ratio: f64,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.resize(&pane_id, ratio).map_err(|e| e.to_string())
}

// -- PTY commands ------------------------------------------------------------

#[tauri::command]
pub fn pty_spawn(
    state: State<AppState>,
    pane_id: String,
    cwd: Option<String>,
) -> Result<(), String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.pty_spawn(&pane_id, cwd.as_deref()).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn pty_write(state: State<AppState>, pane_id: String, data: String) -> Result<(), String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.pty_write(&pane_id, data.as_bytes()).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn pty_resize(
    state: State<AppState>,
    pane_id: String,
    cols: u16,
    rows: u16,
) -> Result<(), String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.pty_resize(&pane_id, cols, rows).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn pty_kill(state: State<AppState>, pane_id: String) -> Result<(), String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.pty_kill(&pane_id).map_err(|e| e.to_string())
}

// -- Agent commands ----------------------------------------------------------

#[tauri::command]
pub fn agent_send(
    state: State<AppState>,
    pane_id: String,
    message: String,
    backend: Option<String>,
    cwd: Option<String>,
) -> Result<(), String> {
    let _ = backend; // TODO: wire backend selection
    let cwd = cwd.unwrap_or_else(|| {
        std::env::current_dir()
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|_| "/tmp".into())
    });
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.chat_send(&pane_id, &message, Some(&cwd)).map_err(|e| e.to_string())
}

// -- Keymap & dispatch commands ----------------------------------------------

#[tauri::command]
pub fn get_keymap(state: State<AppState>) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.keymap().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_commands(state: State<AppState>) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    client.commands().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn dispatch_command(
    state: State<AppState>,
    command: String,
    args: Option<HashMap<String, serde_json::Value>>,
) -> Result<serde_json::Value, String> {
    let mut client = state.client.lock().map_err(|e| e.to_string())?;
    let params = match args {
        Some(map) => serde_json::to_value(map).unwrap_or(serde_json::Value::Null),
        None => serde_json::Value::Null,
    };
    client.request(&command, params).map_err(|e| e.to_string())
}
```

- [ ] **Step 4: Remove unused modules**

Check if `crates/nexus-tauri/src/agent.rs` and `crates/nexus-tauri/src/pty.rs` exist and remove them if they were only used with the embedded engine.

- [ ] **Step 5: Verify compilation**

Run: `cd crates && cargo build -p nexus-tauri`
Expected: Compiles. Tauri is now a thin client.

- [ ] **Step 6: Commit**

```bash
git add crates/nexus-tauri/
git commit -m "feat(tauri): rewrite as thin client using NexusClient and EventSubscription"
```

---

### Task 10: Integration test — daemon + CLI round-trip

Write an integration test that starts the daemon, connects a client, sends commands, and verifies responses.

**Files:**
- Create: `crates/nexus-daemon/tests/integration.rs`

- [ ] **Step 1: Write integration test**

`crates/nexus-daemon/tests/integration.rs`:
```rust
//! Integration test: start daemon, connect client, verify round-trip.

use nexus_client::{NexusClient, JsonRpcRequest, JsonRpcResponse};
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixStream;
use std::path::PathBuf;

/// Start a daemon on a temp socket, return socket paths and child process.
fn start_test_daemon() -> (PathBuf, PathBuf, std::process::Child) {
    let dir = std::env::temp_dir().join(format!("nexus-test-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();

    let cmd_socket = dir.join("nexus.sock");
    let event_socket = dir.join("nexus-events.sock");

    // Clean up any stale sockets
    let _ = std::fs::remove_file(&cmd_socket);
    let _ = std::fs::remove_file(&event_socket);

    // Find the daemon binary
    let daemon = std::env::current_exe().unwrap()
        .parent().unwrap()
        .parent().unwrap()
        .join("nexus-daemon");

    let child = std::process::Command::new(&daemon)
        .arg("--socket")
        .arg(&cmd_socket)
        .spawn()
        .expect("Failed to start daemon");

    // Wait for socket
    for _ in 0..60 {
        if cmd_socket.exists() {
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
    assert!(cmd_socket.exists(), "Daemon socket did not appear");

    (cmd_socket, event_socket, child)
}

fn send_request(stream: &mut BufReader<UnixStream>, writer: &mut UnixStream, method: &str, params: serde_json::Value) -> JsonRpcResponse {
    let req = JsonRpcRequest::new(1, method, params);
    let mut line = serde_json::to_string(&req).unwrap();
    line.push('\n');
    writer.write_all(line.as_bytes()).unwrap();

    let mut buf = String::new();
    stream.read_line(&mut buf).unwrap();
    serde_json::from_str(&buf).unwrap()
}

#[test]
fn daemon_hello_roundtrip() {
    let (cmd_socket, _event_socket, mut child) = start_test_daemon();

    let stream = UnixStream::connect(&cmd_socket).unwrap();
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut writer = stream;

    let resp = send_request(&mut reader, &mut writer, "nexus.hello", serde_json::Value::Null);
    assert!(resp.error.is_none());
    let result = resp.result.unwrap();
    assert!(result.get("version").is_some());
    assert!(result.get("protocol").is_some());

    child.kill().unwrap();
    let _ = std::fs::remove_dir_all(cmd_socket.parent().unwrap());
}

#[test]
fn daemon_layout_operations() {
    let (cmd_socket, _event_socket, mut child) = start_test_daemon();

    let stream = UnixStream::connect(&cmd_socket).unwrap();
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut writer = stream;

    // Get layout
    let resp = send_request(&mut reader, &mut writer, "layout.show", serde_json::Value::Null);
    assert!(resp.error.is_none());

    // Split pane
    let resp = send_request(&mut reader, &mut writer, "pane.split", serde_json::json!({"direction": "vertical"}));
    assert!(resp.error.is_none());

    // List panes
    let resp = send_request(&mut reader, &mut writer, "pane.list", serde_json::Value::Null);
    assert!(resp.error.is_none());
    let panes = resp.result.unwrap();
    assert!(panes.as_array().unwrap().len() >= 2);

    // Navigate
    let resp = send_request(&mut reader, &mut writer, "navigate.left", serde_json::Value::Null);
    assert!(resp.error.is_none());

    child.kill().unwrap();
    let _ = std::fs::remove_dir_all(cmd_socket.parent().unwrap());
}

#[test]
fn daemon_session_operations() {
    let (cmd_socket, _event_socket, mut child) = start_test_daemon();

    let stream = UnixStream::connect(&cmd_socket).unwrap();
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut writer = stream;

    // Session info
    let resp = send_request(&mut reader, &mut writer, "session.info", serde_json::Value::Null);
    assert!(resp.error.is_none());

    // Session list
    let resp = send_request(&mut reader, &mut writer, "session.list", serde_json::Value::Null);
    assert!(resp.error.is_none());

    child.kill().unwrap();
    let _ = std::fs::remove_dir_all(cmd_socket.parent().unwrap());
}

#[test]
fn daemon_unknown_command_returns_error() {
    let (cmd_socket, _event_socket, mut child) = start_test_daemon();

    let stream = UnixStream::connect(&cmd_socket).unwrap();
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut writer = stream;

    let resp = send_request(&mut reader, &mut writer, "bogus.command", serde_json::Value::Null);
    assert!(resp.error.is_some());

    child.kill().unwrap();
    let _ = std::fs::remove_dir_all(cmd_socket.parent().unwrap());
}
```

- [ ] **Step 2: Build daemon binary first**

Run: `cd crates && cargo build -p nexus-daemon`
Expected: Compiles.

- [ ] **Step 3: Run integration tests**

Run: `cd crates && cargo test -p nexus-daemon -- --test-threads=1`
Expected: All integration tests pass.

Note: `--test-threads=1` prevents port conflicts between test daemons.

- [ ] **Step 4: Run full workspace tests**

Run: `cd crates && cargo test`
Expected: All tests pass across all crates.

- [ ] **Step 5: Commit**

```bash
git add crates/nexus-daemon/tests/
git commit -m "test(daemon): add integration tests for daemon round-trip"
```

---

## Post-Implementation Verification

After all tasks complete, verify these invariants from the spec:

1. **Engine lives in daemon only** — `nexus-cli` and `nexus-tauri` have no `nexus-engine` dependency
2. **All surfaces are equal peers** — CLI, Tauri both use `NexusClient::connect()`
3. **Two connections** — daemon binds both `nexus.sock` and `nexus-events.sock`
4. **JSON-RPC 2.0 everywhere** — all messages use the protocol types from `nexus-client`
5. **spawn_blocking** — daemon never holds engine mutex on tokio worker
6. **Single routing path** — server routes all methods through `nexus_engine::dispatch()`
7. **Surfaces never depend on engine** — check `Cargo.toml` dependency graphs

Run: `cd crates && cargo tree -p nexus-cli | grep nexus-engine` — should return nothing.
Run: `cd crates && cargo tree -p nexus-tauri | grep nexus-engine` — should return nothing.
