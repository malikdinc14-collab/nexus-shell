//! Explorer module — ABC trait + adapter registry.
//!
//! Non-native module: external tools (broot, lf, ranger) are the real
//! engines. We define the trait they must satisfy and a thin orchestrator
//! that routes dispatch commands to the active adapter.
//!
//! FsExplorer (std::fs) is the built-in fallback when no external tool
//! is available.

use nexus_core::NexusError;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::path::PathBuf;

// ---------------------------------------------------------------------------
// ABC — the contract any explorer backend must satisfy
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExplorerEntry {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub size: u64,
}

/// Any explorer backend implements this trait.
pub trait ExplorerBackend: Send {
    /// List entries at `path` (single level).
    fn list(&self, path: &str, show_hidden: bool) -> Result<Vec<ExplorerEntry>, NexusError>;

    /// Search for files matching `query` under `root`.
    fn search(&self, root: &str, query: &str) -> Result<Vec<ExplorerEntry>, NexusError> {
        // Default: no search support, return empty
        let _ = (root, query);
        Ok(vec![])
    }

    /// Human-readable name for this backend.
    fn name(&self) -> &str;

    /// Whether this backend is available on the system.
    fn is_available(&self) -> bool;
}

// ---------------------------------------------------------------------------
// Built-in fallback adapter: FsAdapter (std::fs)
// ---------------------------------------------------------------------------

pub struct FsAdapter;

impl ExplorerBackend for FsAdapter {
    fn list(&self, path: &str, show_hidden: bool) -> Result<Vec<ExplorerEntry>, NexusError> {
        let read_dir = std::fs::read_dir(path)
            .map_err(|e| NexusError::Io(format!("{path}: {e}")))?;

        let mut entries: Vec<ExplorerEntry> = Vec::new();

        for entry in read_dir.flatten() {
            let name = entry.file_name().to_string_lossy().to_string();

            if !show_hidden && name.starts_with('.') {
                continue;
            }
            if matches!(name.as_str(), "target" | "node_modules" | "__pycache__") {
                continue;
            }

            let metadata = entry.metadata().map_err(|e| NexusError::Io(format!("{name}: {e}")))?;
            let is_dir = metadata.is_dir();
            let size = if is_dir { 0 } else { metadata.len() };

            entries.push(ExplorerEntry {
                name,
                path: entry.path().to_string_lossy().to_string(),
                is_dir,
                size,
            });
        }

        entries.sort_by(|a, b| {
            b.is_dir
                .cmp(&a.is_dir)
                .then_with(|| a.name.to_lowercase().cmp(&b.name.to_lowercase()))
        });

        Ok(entries)
    }

    fn name(&self) -> &str {
        "fs"
    }

    fn is_available(&self) -> bool {
        true
    }
}

// ---------------------------------------------------------------------------
// BrootAdapter — broot CLI as explorer backend
// ---------------------------------------------------------------------------

pub struct BrootAdapter {
    broot_path: String,
}

impl BrootAdapter {
    pub fn new() -> Self {
        let broot_path = Self::find_broot().unwrap_or_else(|| "broot".into());
        Self { broot_path }
    }

    fn find_broot() -> Option<String> {
        for path in &["broot", "/usr/local/bin/broot", "/usr/bin/broot"] {
            if std::process::Command::new(path)
                .arg("--version")
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false)
            {
                return Some(path.to_string());
            }
        }
        // Check cargo install location
        if let Ok(home) = std::env::var("HOME") {
            let cargo_path = format!("{home}/.cargo/bin/broot");
            if std::path::Path::new(&cargo_path).exists() {
                return Some(cargo_path);
            }
        }
        None
    }
}

impl ExplorerBackend for BrootAdapter {
    fn list(&self, path: &str, show_hidden: bool) -> Result<Vec<ExplorerEntry>, NexusError> {
        // broot --cmd ":print_tree" --no-style outputs a flat tree.
        // For structured data, we use broot's --write-default-conf and parse.
        // Simplest approach: run `broot --sizes --dates --no-style -c ":pt" path`
        // and parse the output. But broot doesn't have a clean JSON list mode.
        //
        // Better approach: use broot's --cmd with :focus + :print_tree for listing,
        // but fall back to direct fs for listing (broot's value is in SEARCH).
        //
        // For v1 listing: use std::fs (same as FsAdapter) — broot's real power
        // is search, not basic listing.
        let read_dir = std::fs::read_dir(path)
            .map_err(|e| NexusError::Io(format!("{path}: {e}")))?;

        let mut entries: Vec<ExplorerEntry> = Vec::new();

        for entry in read_dir.flatten() {
            let name = entry.file_name().to_string_lossy().to_string();

            if !show_hidden && name.starts_with('.') {
                continue;
            }
            if matches!(name.as_str(), "target" | "node_modules" | "__pycache__") {
                continue;
            }

            let metadata = entry.metadata().map_err(|e| NexusError::Io(format!("{name}: {e}")))?;
            let is_dir = metadata.is_dir();
            let size = if is_dir { 0 } else { metadata.len() };

            entries.push(ExplorerEntry {
                name,
                path: entry.path().to_string_lossy().to_string(),
                is_dir,
                size,
            });
        }

        entries.sort_by(|a, b| {
            b.is_dir
                .cmp(&a.is_dir)
                .then_with(|| a.name.to_lowercase().cmp(&b.name.to_lowercase()))
        });

        Ok(entries)
    }

    fn search(&self, root: &str, query: &str) -> Result<Vec<ExplorerEntry>, NexusError> {
        // This is where broot shines — fuzzy search across the tree.
        // `broot --cmd "<query> :print_tree" --color no --no-style <root>`
        let output = std::process::Command::new(&self.broot_path)
            .arg("--color")
            .arg("no")
            .arg("--no-style")
            .arg("--cmd")
            .arg(format!("{query} :print_tree"))
            .arg(root)
            .output()
            .map_err(|e| NexusError::Io(format!("broot failed: {e}")))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(NexusError::Io(format!("broot error: {stderr}")));
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let mut entries = Vec::new();

        for line in stdout.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }

            let path = std::path::Path::new(line);
            let name = path
                .file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_else(|| line.to_string());
            let is_dir = path.is_dir();
            let size = if is_dir {
                0
            } else {
                path.metadata().map(|m| m.len()).unwrap_or(0)
            };

            entries.push(ExplorerEntry {
                name,
                path: line.to_string(),
                is_dir,
                size,
            });
        }

        Ok(entries)
    }

    fn name(&self) -> &str {
        "broot"
    }

    fn is_available(&self) -> bool {
        std::process::Command::new(&self.broot_path)
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
}

// ---------------------------------------------------------------------------
// Orchestrator — owns view state, delegates listing to active backend
// ---------------------------------------------------------------------------

pub struct Explorer {
    backend: Box<dyn ExplorerBackend>,
    root: PathBuf,
    expanded: HashSet<String>,
    show_hidden: bool,
    cursor: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExplorerState {
    pub root: String,
    pub backend: String,
    pub show_hidden: bool,
    pub entries: Vec<ExplorerTreeEntry>,
    pub cursor: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExplorerTreeEntry {
    #[serde(flatten)]
    pub entry: ExplorerEntry,
    pub depth: u32,
    pub expanded: bool,
}

impl Explorer {
    pub fn new(root: &str) -> Self {
        Self {
            backend: Box::new(FsAdapter),
            root: PathBuf::from(root),
            expanded: HashSet::new(),
            show_hidden: false,
            cursor: 0,
        }
    }

    pub fn with_backend(root: &str, backend: Box<dyn ExplorerBackend>) -> Self {
        Self {
            backend,
            root: PathBuf::from(root),
            expanded: HashSet::new(),
            show_hidden: false,
            cursor: 0,
        }
    }

    /// Swap the active backend.
    pub fn set_backend(&mut self, backend: Box<dyn ExplorerBackend>) {
        self.backend = backend;
    }

    pub fn backend_name(&self) -> &str {
        self.backend.name()
    }

    pub fn root(&self) -> &str {
        self.root.to_str().unwrap_or("/")
    }

    pub fn navigate(&mut self, path: &str) {
        self.root = PathBuf::from(path);
        self.expanded.clear();
        self.cursor = 0;
    }

    pub fn up(&mut self) {
        if let Some(parent) = self.root.parent() {
            self.root = parent.to_path_buf();
            self.expanded.clear();
            self.cursor = 0;
        }
    }

    pub fn toggle(&mut self, path: &str) -> bool {
        if self.expanded.contains(path) {
            self.expanded.remove(path);
            false
        } else {
            self.expanded.insert(path.to_string());
            true
        }
    }

    pub fn toggle_hidden(&mut self) -> bool {
        self.show_hidden = !self.show_hidden;
        self.show_hidden
    }

    // ── Cursor navigation ─────────────────────────────────────────

    pub fn cursor_down(&mut self, entry_count: usize) {
        if entry_count > 0 && self.cursor < entry_count - 1 {
            self.cursor += 1;
        }
    }

    pub fn cursor_up(&mut self) {
        if self.cursor > 0 {
            self.cursor -= 1;
        }
    }

    pub fn cursor_index(&self) -> usize {
        self.cursor
    }

    /// Get the entry at cursor position from a tree state.
    pub fn cursor_entry<'a>(&self, entries: &'a [ExplorerTreeEntry]) -> Option<&'a ExplorerTreeEntry> {
        entries.get(self.cursor)
    }

    /// Toggle the entry at cursor. Returns (is_dir, path).
    /// If it's a directory, toggle expand. If file, return path for opening.
    pub fn cursor_toggle(&mut self) -> Result<ExplorerState, NexusError> {
        let state = self.tree()?;
        if let Some(entry) = state.entries.get(self.cursor) {
            let path = entry.entry.path.clone();
            if entry.entry.is_dir {
                self.toggle(&path);
            }
        }
        self.tree()
    }

    /// Collapse the entry at cursor (if dir and expanded) or move to parent dir entry.
    pub fn cursor_collapse(&mut self) -> Result<ExplorerState, NexusError> {
        let state = self.tree()?;
        if let Some(entry) = state.entries.get(self.cursor) {
            let path = entry.entry.path.clone();
            if entry.entry.is_dir && entry.expanded {
                // Collapse this directory
                self.toggle(&path);
            } else if entry.depth > 0 {
                // Move cursor to parent directory
                for i in (0..self.cursor).rev() {
                    if state.entries[i].entry.is_dir && state.entries[i].depth < entry.depth {
                        self.cursor = i;
                        break;
                    }
                }
            }
        }
        self.tree()
    }

    /// Flat listing of a single directory — delegates to backend.
    pub fn list(&self, path: &str) -> Result<Vec<ExplorerEntry>, NexusError> {
        self.backend.list(path, self.show_hidden)
    }

    /// Search — delegates to backend.
    pub fn search(&self, query: &str) -> Result<Vec<ExplorerEntry>, NexusError> {
        let root = self.root.to_string_lossy().to_string();
        self.backend.search(&root, query)
    }

    /// Build visible tree from root, expanding only toggled directories.
    pub fn tree(&mut self) -> Result<ExplorerState, NexusError> {
        let mut entries = Vec::new();
        self.walk(&self.root, 0, &mut entries)?;
        // Clamp cursor to valid range
        if !entries.is_empty() && self.cursor >= entries.len() {
            self.cursor = entries.len() - 1;
        }
        Ok(ExplorerState {
            root: self.root.to_string_lossy().to_string(),
            backend: self.backend.name().to_string(),
            show_hidden: self.show_hidden,
            entries,
            cursor: self.cursor,
        })
    }

    fn walk(
        &self,
        dir: &std::path::Path,
        depth: u32,
        out: &mut Vec<ExplorerTreeEntry>,
    ) -> Result<(), NexusError> {
        let items = self.backend.list(
            dir.to_str().unwrap_or("/"),
            self.show_hidden,
        )?;

        for entry in items {
            let is_expanded = entry.is_dir && self.expanded.contains(&entry.path);
            let path_clone = entry.path.clone();
            out.push(ExplorerTreeEntry {
                entry,
                depth,
                expanded: is_expanded,
            });
            if is_expanded {
                self.walk(std::path::Path::new(&path_clone), depth + 1, out)?;
            }
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn setup_test_dir() -> tempfile::TempDir {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("src")).unwrap();
        std::fs::write(dir.path().join("src/main.rs"), "fn main() {}").unwrap();
        std::fs::write(dir.path().join("Cargo.toml"), "[package]").unwrap();
        std::fs::write(dir.path().join(".hidden"), "secret").unwrap();
        std::fs::create_dir_all(dir.path().join("docs")).unwrap();
        std::fs::write(dir.path().join("docs/README.md"), "# docs").unwrap();
        dir
    }

    // -- FsAdapter tests --

    #[test]
    fn fs_adapter_lists_sorted() {
        let dir = setup_test_dir();
        let adapter = FsAdapter;
        let entries = adapter.list(dir.path().to_str().unwrap(), false).unwrap();
        assert!(entries[0].is_dir);
        assert!(entries.iter().all(|e| !e.name.starts_with('.')));
    }

    #[test]
    fn fs_adapter_shows_hidden() {
        let dir = setup_test_dir();
        let adapter = FsAdapter;
        let entries = adapter.list(dir.path().to_str().unwrap(), true).unwrap();
        assert!(entries.iter().any(|e| e.name.starts_with('.')));
    }

    #[test]
    fn fs_adapter_errors_on_missing() {
        let adapter = FsAdapter;
        assert!(adapter.list("/definitely_not_real_xyz", false).is_err());
    }

    // -- Orchestrator tests --

    #[test]
    fn tree_respects_expanded() {
        let dir = setup_test_dir();
        let mut explorer = Explorer::new(dir.path().to_str().unwrap());

        let state = explorer.tree().unwrap();
        assert!(state.entries.iter().all(|e| e.depth == 0));

        let src_path = dir.path().join("src").to_string_lossy().to_string();
        explorer.toggle(&src_path);
        let state = explorer.tree().unwrap();
        assert!(state.entries.iter().any(|e| e.depth == 1 && e.entry.name == "main.rs"));
    }

    #[test]
    fn navigate_resets_state() {
        let dir = setup_test_dir();
        let mut explorer = Explorer::new(dir.path().to_str().unwrap());
        let src_path = dir.path().join("src").to_string_lossy().to_string();
        explorer.toggle(&src_path);
        assert!(!explorer.expanded.is_empty());

        explorer.navigate("/tmp");
        assert!(explorer.expanded.is_empty());
        assert_eq!(explorer.root(), "/tmp");
    }

    #[test]
    fn up_goes_to_parent() {
        let dir = setup_test_dir();
        let src_path = dir.path().join("src").to_string_lossy().to_string();
        let mut explorer = Explorer::new(&src_path);
        explorer.up();
        assert_eq!(explorer.root(), dir.path().to_str().unwrap());
    }

    #[test]
    fn backend_is_swappable() {
        struct MockBackend;
        impl ExplorerBackend for MockBackend {
            fn list(&self, _path: &str, _show_hidden: bool) -> Result<Vec<ExplorerEntry>, NexusError> {
                Ok(vec![ExplorerEntry {
                    name: "mock.txt".into(),
                    path: "/mock.txt".into(),
                    is_dir: false,
                    size: 42,
                }])
            }
            fn name(&self) -> &str { "mock" }
            fn is_available(&self) -> bool { true }
        }

        let mut explorer = Explorer::new("/tmp");
        assert_eq!(explorer.backend_name(), "fs");

        explorer.set_backend(Box::new(MockBackend));
        assert_eq!(explorer.backend_name(), "mock");

        let entries = explorer.list("/anywhere").unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].name, "mock.txt");
    }

    #[test]
    fn toggle_hidden() {
        let dir = setup_test_dir();
        let mut explorer = Explorer::new(dir.path().to_str().unwrap());
        assert!(!explorer.show_hidden);

        explorer.toggle_hidden();
        let entries = explorer.list(dir.path().to_str().unwrap()).unwrap();
        assert!(entries.iter().any(|e| e.name.starts_with('.')));
    }

    #[test]
    fn state_includes_backend_name() {
        let dir = setup_test_dir();
        let mut explorer = Explorer::new(dir.path().to_str().unwrap());
        let state = explorer.tree().unwrap();
        assert_eq!(state.backend, "fs");
    }
}
