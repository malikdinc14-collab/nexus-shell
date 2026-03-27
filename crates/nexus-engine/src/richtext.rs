use crate::registry::CapabilityRegistry;
use nexus_core::capability::NoteNode;
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
    /// Whether the vault has been opened
    vault_opened: bool,
}

impl RichText {
    pub fn new(registry: Arc<RwLock<CapabilityRegistry>>) -> Self {
        Self {
            registry,
            active_nodes: Arc::new(RwLock::new(HashMap::new())),
            node_cache: Arc::new(RwLock::new(HashMap::new())),
            vault_opened: false,
        }
    }

    /// Open a vault in the best available adapter.
    pub fn open_vault(&mut self, path: &str) -> Result<(), NexusError> {
        let mut reg = self.registry.write().unwrap();
        let adapter = reg.best_richtext_mut()
            .ok_or_else(|| NexusError::NotFound("no richtext adapter available".into()))?;
        adapter.open_vault(path)?;
        self.vault_opened = true;
        Ok(())
    }

    /// Ensure vault is open (auto-open with cwd if not).
    fn ensure_vault(&mut self, cwd: &str) -> Result<(), NexusError> {
        if !self.vault_opened {
            self.open_vault(cwd)?;
        }
        Ok(())
    }

    /// Load a node into a pane via the adapter.
    pub fn load_node(&mut self, pane_id: &str, id_or_path: &str, cwd: &str) -> Result<NoteNode, NexusError> {
        self.ensure_vault(cwd)?;

        let node = {
            let mut reg = self.registry.write().unwrap();
            let adapter = reg.best_richtext_mut()
                .ok_or_else(|| NexusError::NotFound("no richtext adapter available".into()))?;
            adapter.load_node(id_or_path)?
        };

        self.active_nodes.write().unwrap().insert(pane_id.to_string(), node.id.clone());
        self.node_cache.write().unwrap().insert(node.id.clone(), node.clone());
        Ok(node)
    }

    /// Get current state for a pane.
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
