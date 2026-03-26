use crate::capability::{AdapterManifest, Capability, CapabilityType, NoteNode, RichTextCapability};
use crate::error::NexusError;
use std::path::{Path, PathBuf};

/// A markdown-based notes adapter (Obsidian-style).
pub struct NotesAdapter {
    manifest: AdapterManifest,
    vault_path: Option<PathBuf>,
}

impl NotesAdapter {
    pub fn new() -> Self {
        Self {
            manifest: AdapterManifest {
                name: "nexus-notes",
                capability_type: CapabilityType::RichText,
                priority: 100,
                binary: "", // Engine-internal
            },
            vault_path: None,
        }
    }

    fn resolve_path(&self, id_or_path: &str) -> Result<PathBuf, NexusError> {
        let vault = self.vault_path.as_ref()
            .ok_or_else(|| NexusError::InvalidState("no vault open".into()))?;
        
        let path = PathBuf::from(id_or_path);
        if path.is_absolute() {
            Ok(path)
        } else {
            Ok(vault.join(path))
        }
    }
}

impl Default for NotesAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl Capability for NotesAdapter {
    fn manifest(&self) -> &AdapterManifest {
        &self.manifest
    }

    fn is_available(&self) -> bool {
        true
    }
}

impl RichTextCapability for NotesAdapter {
    fn open_vault(&mut self, path: &str) -> Result<(), NexusError> {
        let p = PathBuf::from(path);
        if !p.is_dir() {
            return Err(NexusError::NotFound(format!("vault path is not a directory: {path}")));
        }
        self.vault_path = Some(p);
        Ok(())
    }

    fn load_node(&mut self, id_or_path: &str) -> Result<NoteNode, NexusError> {
        let path = self.resolve_path(id_or_path)?;
        if !path.exists() {
            return Err(NexusError::NotFound(format!("note not found: {}", path.display())));
        }

        let content = std::fs::read_to_string(&path)
            .map_err(|e| NexusError::InvalidState(format!("failed to read note: {e}")))?;
        
        let title = path.file_stem()
            .and_then(|s: &std::ffi::OsStr| s.to_str())
            .unwrap_or("Untitled")
            .to_string();

        Ok(NoteNode {
            id: id_or_path.to_string(),
            path: path.to_string_lossy().to_string(),
            title,
            content,
            tags: vec![], // TODO: parse frontmatter
            backlinks: vec![], // TODO: scan vault
        })
    }

    fn save_node(&mut self, node: NoteNode) -> Result<(), NexusError> {
        let path = PathBuf::from(&node.path);
        std::fs::write(&path, node.content)
            .map_err(|e: std::io::Error| NexusError::InvalidState(format!("failed to save note: {e}")))?;
        Ok(())
    }

    fn search_nodes(&self, _query: &str) -> Result<Vec<NoteNode>, NexusError> {
        // Basic implementation for now
        self.list_nodes()
    }

    fn list_nodes(&self) -> Result<Vec<NoteNode>, NexusError> {
        let vault = self.vault_path.as_ref()
            .ok_or_else(|| NexusError::InvalidState("no vault open".into()))?;
        
        let mut nodes = Vec::new();
        let read_dir = std::fs::read_dir(vault).map_err(|e| NexusError::InvalidState(e.to_string()))?;
        
        for entry in read_dir {
            let entry = entry.map_err(|e| NexusError::InvalidState(e.to_string()))?;
            let path = entry.path();
            
            // Only process .md files
            let is_md = path.extension()
                .and_then(|ext| ext.to_str())
                .map(|s| s == "md")
                .unwrap_or(false);
                
            if is_md {
                let title = path.file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("")
                    .to_string();
                    
                nodes.push(NoteNode {
                    id: path.to_string_lossy().to_string(),
                    path: path.to_string_lossy().to_string(),
                    title,
                    content: String::new(),
                    tags: vec![],
                    backlinks: vec![],
                });
            }
        }
        Ok(nodes)
    }
}
