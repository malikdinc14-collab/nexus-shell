use crate::registry::CapabilityRegistry;
use nexus_core::capability::{NoteNode, RichTextCapability};
use nexus_core::error::NexusError;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

/// Manages active RichText sessions (open nodes, vault state).
pub struct RichText {
    pub registry: Arc<RwLock<CapabilityRegistry>>,
    /// Map of Pane ID -> Active Node ID
    pub active_nodes: Arc<RwLock<HashMap<String, String>>>,
    /// Cache of loaded nodes (for performance)
    pub node_cache: Arc<RwLock<HashMap<String, NoteNode>>>,
}

impl RichText {
    pub fn new(registry: Arc<RwLock<CapabilityRegistry>>) -> Self {
        Self {
            registry,
            active_nodes: Arc::new(RwLock::new(HashMap::new())),
            node_cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Open a vault in the best available adapter
    pub fn open_vault(&self, path: &str) -> Result<(), NexusError> {
        let reg = self.registry.read().unwrap();
        let adapter = reg.best_richtext()
            .ok_or_else(|| NexusError::NotFound("no richtext adapter available".into()))?;
        
        // We need a way to call mut methods on the adapter.
        // For now, we'll assume the registry provides a way to get a mut ref or we use interior mutability.
        // Actually, the registry currently returns &Box<dyn RichTextCapability>.
        // We'll need to update the registry or use a different pattern.
        
        // Stub for now: real implementation would find the adapter and call open_vault.
        println!("Opening vault at {}", path);
        Ok(())
    }

    /// Load a node into a pane
    pub fn load_node(&self, pane_id: &str, id_or_path: &str) -> Result<NoteNode, NexusError> {
        let reg = self.registry.read().unwrap();
        let adapter = reg.best_richtext()
            .ok_or_else(|| NexusError::NotFound("no richtext adapter available".into()))?;

        // In a real implementation, we'd call adapter.load_node().
        // For the stub, we'll just record the activity.
        self.active_nodes.write().unwrap().insert(pane_id.to_string(), id_or_path.to_string());
        
        // Return a mock node for now to prove the flow
        let node = NoteNode {
            id: id_or_path.to_string(),
            path: id_or_path.to_string(),
            title: "Mock Note".into(),
            content: "# Welcome to Nexus Notes\n\nThis is a placeholder.".into(),
            tags: vec!["nexus".into(), "notes".into()],
            backlinks: vec![],
        };
        self.node_cache.write().unwrap().insert(id_or_path.to_string(), node.clone());
        Ok(node)
    }

    /// Get current state for a pane
    pub fn state(&self, pane_id: &str) -> Result<Option<NoteNode>, NexusError> {
        let active = self.active_nodes.read().unwrap();
        let node_id = match active.get(pane_id) {
            Some(id) => id,
            None => return Ok(None),
        };
        
        let cache = self.node_cache.read().unwrap();
        Ok(cache.get(node_id).cloned())
    }
}
