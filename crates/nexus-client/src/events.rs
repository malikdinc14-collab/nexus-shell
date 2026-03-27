//! EventSubscription — synchronous filtered event stream from the daemon.

use crate::protocol::{JsonRpcNotification, JsonRpcRequest, JsonRpcResponse};
use nexus_core::NexusError;
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::sync::atomic::{AtomicU64, Ordering};

#[cfg(unix)]
type InnerStream = std::os::unix::net::UnixStream;

#[cfg(not(unix))]
type InnerStream = std::net::TcpStream;

/// A connection to the daemon's event socket with active subscription.
pub struct EventSubscription {
    reader: BufReader<InnerStream>,
    writer: InnerStream,
    next_id: AtomicU64,
}

impl EventSubscription {
    /// Connect to the event socket and subscribe to the given patterns (Unix).
    #[cfg(unix)]
    pub fn subscribe(
        patterns: &[&str],
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<Self, NexusError> {
        let path = nexus_core::constants::events_socket_path();
        Self::subscribe_to(path.to_str().unwrap_or(""), patterns, filter)
    }

    /// Connect to a specific event socket path (for testing) (Unix).
    #[cfg(unix)]
    pub fn subscribe_to(
        path: &str,
        patterns: &[&str],
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<Self, NexusError> {
        let stream = InnerStream::connect(path)
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

    /// Connect to the event socket and subscribe to the given patterns (Windows).
    #[cfg(not(unix))]
    pub fn subscribe(
        patterns: &[&str],
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<Self, NexusError> {
        let addr = nexus_core::constants::event_addr();
        Self::subscribe_to(addr, patterns, filter)
    }

    /// Connect to a specific TCP address (for testing) (Windows).
    #[cfg(not(unix))]
    pub fn subscribe_to(
        addr: std::net::SocketAddr,
        patterns: &[&str],
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> Result<Self, NexusError> {
        let stream = InnerStream::connect(addr)
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
            .map_err(|e| NexusError::Protocol(format!("parse event: {e}")))
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
