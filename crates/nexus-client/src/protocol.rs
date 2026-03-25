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
