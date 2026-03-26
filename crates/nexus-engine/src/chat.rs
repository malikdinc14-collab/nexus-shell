//! Chat module — ABC trait + adapter registry.
//!
//! Non-native module: external LLM providers (Claude, OpenCode, Ollama)
//! are the real engines. We define the trait they must satisfy and a thin
//! orchestrator that manages conversation state per pane.

use nexus_core::NexusError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::content_tabs::{ContentTab, ContentTabState, TabProvider};

// ---------------------------------------------------------------------------
// ABC — the contract any chat backend must satisfy
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,      // "user", "assistant", "system"
    pub content: String,
    pub timestamp: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatBackendInfo {
    pub name: String,
    pub model: Option<String>,
    pub streaming: bool,
}

/// Any chat backend implements this trait.
pub trait ChatBackend: Send {
    /// Human-readable name.
    fn name(&self) -> &str;

    /// Backend info for surfaces.
    fn info(&self) -> ChatBackendInfo;

    /// Whether this backend is available.
    fn is_available(&self) -> bool;

    /// Send a message synchronously, return the response.
    /// For v1, blocking is fine. Streaming comes in v2.
    fn send(&self, messages: &[ChatMessage], cwd: &str) -> Result<String, NexusError>;
}

// ---------------------------------------------------------------------------
// Built-in fallback: EchoBackend (for testing / when no LLM configured)
// ---------------------------------------------------------------------------

pub struct EchoBackend;

impl ChatBackend for EchoBackend {
    fn name(&self) -> &str { "echo" }

    fn info(&self) -> ChatBackendInfo {
        ChatBackendInfo {
            name: "echo".into(),
            model: None,
            streaming: false,
        }
    }

    fn is_available(&self) -> bool { true }

    fn send(&self, messages: &[ChatMessage], _cwd: &str) -> Result<String, NexusError> {
        if let Some(last) = messages.last() {
            Ok(format!("[echo] {}", last.content))
        } else {
            Ok("[echo] (empty)".into())
        }
    }
}

// ---------------------------------------------------------------------------
// Conversation — per-pane chat state
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Conversation {
    pub pane_id: String,
    pub messages: Vec<ChatMessage>,
    pub backend: String,
}

// ---------------------------------------------------------------------------
// Orchestrator
// ---------------------------------------------------------------------------

/// Multiple conversations per pane with active index.
#[derive(Debug, Clone)]
struct PaneConversations {
    items: Vec<Conversation>,
    active: usize,
}

impl PaneConversations {
    fn new() -> Self {
        Self { items: Vec::new(), active: 0 }
    }

    fn active_conv(&self) -> Option<&Conversation> {
        self.items.get(self.active)
    }

    fn active_conv_mut(&mut self) -> Option<&mut Conversation> {
        self.items.get_mut(self.active)
    }
}

pub struct Chat {
    backend: Box<dyn ChatBackend>,
    conversations: HashMap<String, PaneConversations>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatState {
    pub backend: ChatBackendInfo,
    pub conversations: Vec<String>, // pane_ids with active conversations
}

impl Chat {
    pub fn new() -> Self {
        Self {
            backend: Box::new(EchoBackend),
            conversations: HashMap::new(),
        }
    }

    pub fn with_backend(backend: Box<dyn ChatBackend>) -> Self {
        Self {
            backend,
            conversations: HashMap::new(),
        }
    }

    pub fn set_backend(&mut self, backend: Box<dyn ChatBackend>) {
        self.backend = backend;
    }

    pub fn backend_name(&self) -> &str {
        self.backend.name()
    }

    pub fn backend_info(&self) -> ChatBackendInfo {
        self.backend.info()
    }

    /// Get or create the active conversation for a pane.
    fn ensure_conversation(&mut self, pane_id: &str) -> &mut Conversation {
        let backend_name = self.backend.name().to_string();
        let pane = self.conversations.entry(pane_id.to_string()).or_insert_with(|| {
            let mut pc = PaneConversations::new();
            pc.items.push(Conversation {
                pane_id: pane_id.to_string(),
                messages: Vec::new(),
                backend: backend_name,
            });
            pc
        });
        pane.active_conv_mut().unwrap()
    }

    /// Send a user message, get assistant response. Returns the full conversation.
    pub fn send(&mut self, pane_id: &str, message: &str, cwd: &str) -> Result<Conversation, NexusError> {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let conv = self.ensure_conversation(pane_id);
        conv.messages.push(ChatMessage {
            role: "user".into(),
            content: message.to_string(),
            timestamp: now,
        });

        let msgs = conv.messages.clone();
        let response = self.backend.send(&msgs, cwd)?;

        let pane = self.conversations.get_mut(pane_id).unwrap();
        let conv = pane.active_conv_mut().unwrap();
        conv.messages.push(ChatMessage {
            role: "assistant".into(),
            content: response,
            timestamp: now,
        });

        Ok(conv.clone())
    }

    /// Get active conversation history for a pane.
    pub fn history(&self, pane_id: &str) -> Option<&Conversation> {
        self.conversations.get(pane_id)?.active_conv()
    }

    /// Clear the active conversation.
    pub fn clear(&mut self, pane_id: &str) -> bool {
        if let Some(pane) = self.conversations.get_mut(pane_id) {
            if let Some(conv) = pane.active_conv_mut() {
                conv.messages.clear();
                return true;
            }
        }
        false
    }

    /// Start a new conversation in a pane (adds to the list).
    pub fn new_conversation(&mut self, pane_id: &str) -> &Conversation {
        let backend_name = self.backend.name().to_string();
        let pane = self.conversations.entry(pane_id.to_string()).or_insert_with(PaneConversations::new);
        let conv = Conversation {
            pane_id: pane_id.to_string(),
            messages: Vec::new(),
            backend: backend_name,
        };
        pane.items.push(conv);
        pane.active = pane.items.len() - 1;
        &pane.items[pane.active]
    }

    /// Full state for surfaces.
    pub fn state(&self) -> ChatState {
        ChatState {
            backend: self.backend.info(),
            conversations: self.conversations.keys().cloned().collect(),
        }
    }
}

// ---------------------------------------------------------------------------
// TabProvider implementation
// ---------------------------------------------------------------------------

impl TabProvider for Chat {
    fn content_tabs(&self, pane_id: &str) -> Option<ContentTabState> {
        let pane = self.conversations.get(pane_id)?;
        if pane.items.is_empty() {
            return None;
        }
        Some(ContentTabState {
            tabs: pane.items.iter().enumerate().map(|(i, c)| {
                let name = if c.messages.is_empty() {
                    format!("New chat {}", i + 1)
                } else {
                    // Use first user message as tab name (truncated)
                    c.messages.iter()
                        .find(|m| m.role == "user")
                        .map(|m| {
                            let s = &m.content;
                            if s.len() > 20 { format!("{}...", &s[..20]) } else { s.clone() }
                        })
                        .unwrap_or_else(|| format!("Chat {}", i + 1))
                };
                ContentTab {
                    id: format!("{}-{}", pane_id, i),
                    name,
                    modified: false,
                    preview: false,
                }
            }).collect(),
            active: pane.active,
        })
    }

    fn switch_content_tab(&mut self, pane_id: &str, index: usize) -> Result<ContentTabState, NexusError> {
        let pane = self.conversations.get_mut(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no conversations in {pane_id}")))?;
        if index >= pane.items.len() {
            return Err(NexusError::InvalidState(format!("index {index} out of range ({})", pane.items.len())));
        }
        pane.active = index;
        self.content_tabs(pane_id).ok_or_else(|| NexusError::Other("unreachable".into()))
    }

    fn close_content_tab(&mut self, pane_id: &str, index: usize) -> Result<Option<ContentTabState>, NexusError> {
        let pane = self.conversations.get_mut(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no conversations in {pane_id}")))?;
        if index >= pane.items.len() {
            return Err(NexusError::InvalidState(format!("index {index} out of range ({})", pane.items.len())));
        }
        pane.items.remove(index);
        if pane.items.is_empty() {
            self.conversations.remove(pane_id);
            return Ok(None);
        }
        if pane.active >= pane.items.len() {
            pane.active = pane.items.len() - 1;
        }
        Ok(self.content_tabs(pane_id))
    }

    fn supports_content_tabs(&self) -> bool { true }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn echo_backend_works() {
        let backend = EchoBackend;
        let msgs = vec![ChatMessage {
            role: "user".into(),
            content: "hello".into(),
            timestamp: 0,
        }];
        let resp = backend.send(&msgs, "/tmp").unwrap();
        assert!(resp.contains("hello"));
    }

    #[test]
    fn conversation_lifecycle() {
        let mut chat = Chat::new();

        // Send
        let conv = chat.send("pane-1", "hi", "/tmp").unwrap();
        assert_eq!(conv.messages.len(), 2);
        assert_eq!(conv.messages[0].role, "user");
        assert_eq!(conv.messages[1].role, "assistant");

        // History
        let hist = chat.history("pane-1").unwrap();
        assert_eq!(hist.messages.len(), 2);

        // Second message
        let conv = chat.send("pane-1", "how are you", "/tmp").unwrap();
        assert_eq!(conv.messages.len(), 4);

        // Clear — clears messages but conversation entry remains
        assert!(chat.clear("pane-1"));
        let hist = chat.history("pane-1").unwrap();
        assert!(hist.messages.is_empty());
    }

    #[test]
    fn backend_swappable() {
        struct MockLLM;
        impl ChatBackend for MockLLM {
            fn name(&self) -> &str { "mock-llm" }
            fn info(&self) -> ChatBackendInfo {
                ChatBackendInfo { name: "mock-llm".into(), model: Some("test-7b".into()), streaming: false }
            }
            fn is_available(&self) -> bool { true }
            fn send(&self, _msgs: &[ChatMessage], _cwd: &str) -> Result<String, NexusError> {
                Ok("I am a mock LLM".into())
            }
        }

        let mut chat = Chat::new();
        assert_eq!(chat.backend_name(), "echo");

        chat.set_backend(Box::new(MockLLM));
        assert_eq!(chat.backend_name(), "mock-llm");

        let conv = chat.send("p1", "test", "/tmp").unwrap();
        assert_eq!(conv.messages[1].content, "I am a mock LLM");
    }

    #[test]
    fn state_lists_conversations() {
        let mut chat = Chat::new();
        chat.send("p1", "a", "/tmp").unwrap();
        chat.send("p2", "b", "/tmp").unwrap();
        let state = chat.state();
        assert_eq!(state.conversations.len(), 2);
        assert_eq!(state.backend.name, "echo");
    }

    #[test]
    fn no_history_returns_none() {
        let chat = Chat::new();
        assert!(chat.history("nonexistent").is_none());
    }
}
