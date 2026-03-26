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
