# Task 8: Add client convenience methods for session and layout persistence

## Context

The nexus-client crate exposes `NexusClient` in `crates/nexus-client/src/client.rs`.
It already has a `request()` method that does synchronous JSON-RPC. Your job is to
add convenience wrappers for the new persistence dispatch methods.

## File to modify

`crates/nexus-client/src/client.rs`

## What to add

Add these methods to the `NexusClient` impl block. Insert them after the existing
`session_info` and `session_create` methods:

```rust
pub fn session_save(&mut self, name: &str) -> Result<serde_json::Value, NexusError> {
    self.request("session.save", serde_json::json!({"name": name}))
}

pub fn session_restore(&mut self, name: &str) -> Result<serde_json::Value, NexusError> {
    self.request("session.restore", serde_json::json!({"name": name}))
}

pub fn session_delete(&mut self, name: &str) -> Result<serde_json::Value, NexusError> {
    self.request("session.delete", serde_json::json!({"name": name}))
}

pub fn session_snapshots(&mut self) -> Result<serde_json::Value, NexusError> {
    self.request("session.snapshots", serde_json::Value::Null)
}

pub fn layout_export(
    &mut self,
    name: &str,
    description: Option<&str>,
    scope: Option<&str>,
) -> Result<serde_json::Value, NexusError> {
    let mut params = serde_json::json!({"name": name});
    if let Some(desc) = description {
        params["description"] = serde_json::json!(desc);
    }
    if let Some(s) = scope {
        params["scope"] = serde_json::json!(s);
    }
    self.request("layout.export", params)
}

pub fn layout_import(&mut self, name: &str) -> Result<serde_json::Value, NexusError> {
    self.request("layout.import", serde_json::json!({"name": name}))
}

pub fn layout_list(&mut self) -> Result<serde_json::Value, NexusError> {
    self.request("layout.list", serde_json::Value::Null)
}
```

## Verification

Run: `cargo build -p nexus-client`
Expected: Compiles with no errors.

## Done signal

Move this file to `tasks/antigravity/done/task-08-client-methods.md` when complete.
