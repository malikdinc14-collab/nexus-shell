//! FsExplorer — ExplorerCapability backed by `std::fs`.
//!
//! Built-in filesystem explorer that requires no external tools.
//! Filters hidden files (names starting with `.`) and returns entries
//! sorted directories-first, then alphabetically.

use crate::capability::{
    AdapterManifest, Capability, CapabilityType, DirEntry, ExplorerCapability,
};
use crate::error::NexusError;

pub struct FsExplorer {
    manifest: AdapterManifest,
}

impl FsExplorer {
    pub fn new() -> Self {
        Self {
            manifest: AdapterManifest {
                name: "fs",
                capability_type: CapabilityType::Explorer,
                priority: 50,
                binary: "",
            },
        }
    }
}

impl Default for FsExplorer {
    fn default() -> Self {
        Self::new()
    }
}

impl Capability for FsExplorer {
    fn manifest(&self) -> &AdapterManifest {
        &self.manifest
    }

    fn is_available(&self) -> bool {
        true
    }
}

impl ExplorerCapability for FsExplorer {
    fn list_directory(&self, path: &str) -> Result<Vec<DirEntry>, NexusError> {
        let read_dir = std::fs::read_dir(path)?;

        let mut entries: Vec<DirEntry> = Vec::new();

        for entry in read_dir {
            let entry = entry?;
            let name = entry.file_name().to_string_lossy().to_string();

            // Filter hidden files
            if name.starts_with('.') {
                continue;
            }

            let metadata = entry.metadata()?;
            let is_dir = metadata.is_dir();
            let size = if is_dir { 0 } else { metadata.len() };

            entries.push(DirEntry {
                name,
                path: entry.path().to_string_lossy().to_string(),
                is_dir,
                size,
            });
        }

        // Sort: directories first, then alphabetically within each group
        entries.sort_by(|a, b| {
            b.is_dir
                .cmp(&a.is_dir)
                .then_with(|| a.name.to_lowercase().cmp(&b.name.to_lowercase()))
        });

        Ok(entries)
    }

    fn get_selection(&self) -> Option<String> {
        None
    }

    fn trigger_action(&mut self, action: &str, _payload: &str) -> Result<(), NexusError> {
        Err(NexusError::InvalidState(format!(
            "FsExplorer does not support action: {action}"
        )))
    }

    fn get_launch_command(&self) -> Option<String> {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capability::Capability;

    #[test]
    fn fs_explorer_manifest() {
        let adapter = FsExplorer::new();
        let m = adapter.manifest();
        assert_eq!(m.name, "fs");
        assert_eq!(m.capability_type, CapabilityType::Explorer);
    }

    #[test]
    fn fs_explorer_is_always_available() {
        let adapter = FsExplorer::new();
        assert!(adapter.is_available());
    }

    #[test]
    fn fs_explorer_list_directory() {
        let adapter = FsExplorer::new();
        let entries = adapter.list_directory("/tmp").unwrap();
        // /tmp exists and is listable
        let _ = entries;
    }

    #[test]
    fn fs_explorer_list_nonexistent_errors() {
        let adapter = FsExplorer::new();
        let result = adapter.list_directory("/definitely_not_a_real_path_xyz");
        assert!(result.is_err());
    }

    #[test]
    fn fs_explorer_get_launch_command_is_none() {
        let adapter = FsExplorer::new();
        assert!(adapter.get_launch_command().is_none());
    }

    #[test]
    fn fs_explorer_trigger_action_errors() {
        let mut adapter = FsExplorer::new();
        let result = adapter.trigger_action("open", "/tmp");
        assert!(result.is_err());
    }

    #[test]
    fn fs_explorer_filters_hidden_files() {
        // Create a temp dir with hidden and visible files
        let dir = std::env::temp_dir().join("nexus_fs_explorer_test");
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join(".hidden"), "").unwrap();
        std::fs::write(dir.join("visible.txt"), "").unwrap();

        let adapter = FsExplorer::new();
        let entries = adapter
            .list_directory(dir.to_str().unwrap())
            .unwrap();

        assert!(entries.iter().all(|e| !e.name.starts_with('.')));
        assert!(entries.iter().any(|e| e.name == "visible.txt"));

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn fs_explorer_sorts_dirs_first() {
        let dir = std::env::temp_dir().join("nexus_fs_explorer_sort_test");
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("file_a.txt"), "").unwrap();
        std::fs::create_dir_all(dir.join("dir_b")).unwrap();

        let adapter = FsExplorer::new();
        let entries = adapter
            .list_directory(dir.to_str().unwrap())
            .unwrap();

        assert!(entries[0].is_dir, "first entry should be a directory");
        assert!(!entries[1].is_dir, "second entry should be a file");

        let _ = std::fs::remove_dir_all(&dir);
    }
}
