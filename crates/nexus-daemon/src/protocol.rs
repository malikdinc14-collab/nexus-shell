//! Wire protocol — newline-delimited JSON over unix socket.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A command sent from client to daemon.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Request {
    /// Dotted command name: "stack.push", "layout.show", "session.info"
    pub cmd: String,
    /// Command arguments (string key-value for stack ops, typed for others)
    #[serde(default)]
    pub args: HashMap<String, serde_json::Value>,
}

/// Response from daemon to client.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Response {
    pub status: String,
    #[serde(default)]
    pub data: serde_json::Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl Response {
    pub fn ok(data: serde_json::Value) -> Self {
        Self {
            status: "ok".into(),
            data,
            error: None,
        }
    }

    pub fn err(msg: &str) -> Self {
        Self {
            status: "error".into(),
            data: serde_json::Value::Null,
            error: Some(msg.into()),
        }
    }
}
