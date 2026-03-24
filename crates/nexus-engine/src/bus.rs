//! Event bus with typed events, wildcard subscriptions, and dead subscriber detection.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};

// ---------------------------------------------------------------------------
// Event types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EventType {
    StackPush,
    StackPop,
    StackRotate,
    StackSwitch,
    StackReplace,
    StackClose,
    PaneSplit,
    PaneKill,
    TabSwitch,
    ProfileSwitch,
    PackEnable,
    PackDisable,
    ConfigReload,
    CompositionSwitch,
    WorkspaceSave,
    WorkspaceRestore,
    ProjectDiscovered,
    BootStart,
    BootProgress,
    BootComplete,
    BootItemOk,
    BootItemFail,
    BootShutdown,
    Custom,
}

impl EventType {
    /// Dotted string form for pattern matching.
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::StackPush => "stack.push",
            Self::StackPop => "stack.pop",
            Self::StackRotate => "stack.rotate",
            Self::StackSwitch => "stack.switch",
            Self::StackReplace => "stack.replace",
            Self::StackClose => "stack.close",
            Self::PaneSplit => "pane.split",
            Self::PaneKill => "pane.kill",
            Self::TabSwitch => "tab.switch",
            Self::ProfileSwitch => "profile.switch",
            Self::PackEnable => "pack.enable",
            Self::PackDisable => "pack.disable",
            Self::ConfigReload => "config.reload",
            Self::CompositionSwitch => "composition.switch",
            Self::WorkspaceSave => "workspace.save",
            Self::WorkspaceRestore => "workspace.restore",
            Self::ProjectDiscovered => "project.discovered",
            Self::BootStart => "boot.start",
            Self::BootProgress => "boot.progress",
            Self::BootComplete => "boot.complete",
            Self::BootItemOk => "boot.item.ok",
            Self::BootItemFail => "boot.item.fail",
            Self::BootShutdown => "boot.shutdown",
            Self::Custom => "custom",
        }
    }
}

// ---------------------------------------------------------------------------
// TypedEvent
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypedEvent {
    pub event_type: EventType,
    pub source: String,
    pub payload: HashMap<String, serde_json::Value>,
    pub timestamp: f64,
}

impl TypedEvent {
    pub fn new(event_type: EventType, source: &str) -> Self {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);
        Self {
            event_type,
            source: source.to_string(),
            payload: HashMap::new(),
            timestamp,
        }
    }

    pub fn with_payload(mut self, key: &str, value: impl Into<serde_json::Value>) -> Self {
        self.payload.insert(key.to_string(), value.into());
        self
    }
}

// ---------------------------------------------------------------------------
// EventBus
// ---------------------------------------------------------------------------

type Callback = Box<dyn Fn(&TypedEvent) + Send + Sync>;

struct Subscriber {
    callback: Callback,
    failures: u32,
    dead: bool,
}

/// Event bus supporting wildcard patterns and dead subscriber detection.
///
/// Patterns use glob-style wildcards:
///   - `stack.*` matches `stack.push`, `stack.pop`, etc.
///   - `*.*` matches any dotted event
pub struct EventBus {
    subscribers: HashMap<String, Vec<Subscriber>>,
    history: VecDeque<TypedEvent>,
    max_history: usize,
    dead_threshold: u32,
}

impl EventBus {
    pub fn new() -> Self {
        Self {
            subscribers: HashMap::new(),
            history: VecDeque::with_capacity(100),
            max_history: 100,
            dead_threshold: 3,
        }
    }

    /// Register a callback to receive events matching `pattern`.
    pub fn subscribe<F>(&mut self, pattern: &str, callback: F)
    where
        F: Fn(&TypedEvent) + Send + Sync + 'static,
    {
        self.subscribers
            .entry(pattern.to_string())
            .or_default()
            .push(Subscriber {
                callback: Box::new(callback),
                failures: 0,
                dead: false,
            });
    }

    /// Deliver an event to all matching subscribers. Returns delivery count.
    pub fn publish(&mut self, event: TypedEvent) -> u32 {
        // Store in history
        if self.history.len() >= self.max_history {
            self.history.pop_front();
        }
        self.history.push_back(event.clone());

        let event_name = event.source.as_str();
        let mut delivered = 0u32;

        for (pattern, subscribers) in self.subscribers.iter_mut() {
            if !Self::matches(pattern, event_name) {
                continue;
            }
            for sub in subscribers.iter_mut() {
                if sub.dead {
                    continue;
                }
                // In Rust, closures don't panic by default like Python exceptions.
                // We use catch_unwind for robustness but callbacks should not panic.
                let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                    (sub.callback)(&event);
                }));
                match result {
                    Ok(()) => {
                        sub.failures = 0;
                        delivered += 1;
                    }
                    Err(_) => {
                        sub.failures += 1;
                        if sub.failures >= self.dead_threshold {
                            sub.dead = true;
                        }
                    }
                }
            }
        }
        delivered
    }

    /// Glob-style pattern matching: `*` matches any segment, `?` matches one char.
    fn matches(pattern: &str, event_name: &str) -> bool {
        // Simple glob: split on segments
        let pat_parts: Vec<&str> = pattern.split('.').collect();
        let name_parts: Vec<&str> = event_name.split('.').collect();

        if pat_parts.len() != name_parts.len() {
            return false;
        }

        pat_parts
            .iter()
            .zip(name_parts.iter())
            .all(|(p, n)| *p == "*" || *p == *n)
    }

    /// Number of active (non-dead) subscriptions.
    pub fn subscriber_count(&self) -> usize {
        self.subscribers
            .values()
            .flat_map(|subs| subs.iter())
            .filter(|s| !s.dead)
            .count()
    }

    /// Recent event history.
    pub fn history(&self) -> &VecDeque<TypedEvent> {
        &self.history
    }

    pub fn clear_history(&mut self) {
        self.history.clear();
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, atomic::{AtomicU32, Ordering}};

    #[test]
    fn publish_delivers_to_exact_match() {
        let mut bus = EventBus::new();
        let count = Arc::new(AtomicU32::new(0));
        let c = count.clone();
        bus.subscribe("stack.push", move |_| {
            c.fetch_add(1, Ordering::SeqCst);
        });
        let event = TypedEvent::new(EventType::StackPush, "stack.push");
        bus.publish(event);
        assert_eq!(count.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn wildcard_matches_all_in_namespace() {
        let mut bus = EventBus::new();
        let count = Arc::new(AtomicU32::new(0));
        let c = count.clone();
        bus.subscribe("stack.*", move |_| {
            c.fetch_add(1, Ordering::SeqCst);
        });

        bus.publish(TypedEvent::new(EventType::StackPush, "stack.push"));
        bus.publish(TypedEvent::new(EventType::StackClose, "stack.close"));
        bus.publish(TypedEvent::new(EventType::PaneSplit, "pane.split"));

        assert_eq!(count.load(Ordering::SeqCst), 2);
    }

    #[test]
    fn no_match_for_different_pattern() {
        let mut bus = EventBus::new();
        let count = Arc::new(AtomicU32::new(0));
        let c = count.clone();
        bus.subscribe("pane.*", move |_| {
            c.fetch_add(1, Ordering::SeqCst);
        });
        bus.publish(TypedEvent::new(EventType::StackPush, "stack.push"));
        assert_eq!(count.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn history_is_bounded() {
        let mut bus = EventBus::new();
        bus.max_history = 5;
        for i in 0..10 {
            bus.publish(TypedEvent::new(EventType::Custom, &format!("ev.{i}")));
        }
        assert_eq!(bus.history().len(), 5);
    }

    #[test]
    fn event_payload_builder() {
        let event = TypedEvent::new(EventType::StackPush, "stack.push")
            .with_payload("stack_id", "s1")
            .with_payload("pane", "p1");
        assert_eq!(event.payload.get("stack_id").unwrap(), "s1");
        assert_eq!(event.payload.get("pane").unwrap(), "p1");
    }
}
