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
        let notif = nexus_client::protocol::JsonRpcNotification::new(
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
                if conn.sub.matches(&event) && !conn.write_event(&event).await {
                    to_remove.push(i);
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
