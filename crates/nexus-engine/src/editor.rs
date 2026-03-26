//! Editor module — ABC trait + adapter registry.
//!
//! Non-native module: external editors (nvim, helix, nano) are the real
//! engines. We define the trait they must satisfy and a thin orchestrator
//! that manages buffer state per pane.
//!
//! NativeAdapter is a simple built-in fallback (read-only file viewer).
//! Real editing power comes from nvim (headless RPC) or helix adapters.

use nexus_core::NexusError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::content_tabs::{ContentTab, ContentTabState, TabProvider};

// ---------------------------------------------------------------------------
// ABC — the contract any editor backend must satisfy
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BufferInfo {
    pub path: String,
    pub name: String,
    pub modified: bool,
    pub line_count: usize,
    pub language: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EditorBackendInfo {
    pub name: String,
    pub version: Option<String>,
    pub supports_lsp: bool,
    pub supports_syntax: bool,
}

/// Any editor backend implements this trait.
pub trait EditorBackend: Send {
    /// Human-readable name.
    fn name(&self) -> &str;

    /// Backend capabilities info.
    fn info(&self) -> EditorBackendInfo;

    /// Whether this backend is available on the system.
    fn is_available(&self) -> bool;

    /// Read file contents. Returns (content, line_count).
    fn read(&self, path: &str) -> Result<(String, usize), NexusError>;

    /// Write content to file.
    fn write(&self, path: &str, content: &str) -> Result<(), NexusError>;

    /// Detect language from file extension.
    fn detect_language(&self, path: &str) -> Option<String> {
        let ext = path.rsplit('.').next()?;
        Some(match ext {
            "rs" => "rust",
            "ts" | "tsx" => "typescript",
            "js" | "jsx" => "javascript",
            "py" => "python",
            "go" => "go",
            "c" | "h" => "c",
            "cpp" | "hpp" | "cc" => "cpp",
            "java" => "java",
            "rb" => "ruby",
            "lua" => "lua",
            "sh" | "bash" | "zsh" => "shell",
            "json" => "json",
            "yaml" | "yml" => "yaml",
            "toml" => "toml",
            "md" => "markdown",
            "html" => "html",
            "css" => "css",
            _ => return None,
        }.to_string())
    }
}

// ---------------------------------------------------------------------------
// Built-in fallback: NativeAdapter (std::fs read/write)
// ---------------------------------------------------------------------------

pub struct NativeAdapter;

impl EditorBackend for NativeAdapter {
    fn name(&self) -> &str { "native" }

    fn info(&self) -> EditorBackendInfo {
        EditorBackendInfo {
            name: "native".into(),
            version: None,
            supports_lsp: false,
            supports_syntax: false,
        }
    }

    fn is_available(&self) -> bool { true }

    fn read(&self, path: &str) -> Result<(String, usize), NexusError> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| NexusError::Io(format!("{path}: {e}")))?;
        let line_count = content.lines().count();
        Ok((content, line_count))
    }

    fn write(&self, path: &str, content: &str) -> Result<(), NexusError> {
        std::fs::write(path, content)
            .map_err(|e| NexusError::Io(format!("{path}: {e}")))
    }
}

// ---------------------------------------------------------------------------
// NvimAdapter — nvim headless as editor backend
// ---------------------------------------------------------------------------

pub struct NvimAdapter {
    nvim_path: String,
    version: Option<String>,
}

impl NvimAdapter {
    pub fn new() -> Self {
        let nvim_path = Self::find_nvim().unwrap_or_else(|| "nvim".into());
        let version = Self::detect_version(&nvim_path);
        Self { nvim_path, version }
    }

    fn find_nvim() -> Option<String> {
        for path in &["nvim", "/usr/bin/nvim", "/usr/local/bin/nvim", "/snap/bin/nvim"] {
            if std::process::Command::new(path)
                .arg("--version")
                .output()
                .is_ok()
            {
                return Some(path.to_string());
            }
        }
        None
    }

    fn detect_version(path: &str) -> Option<String> {
        let output = std::process::Command::new(path)
            .arg("--version")
            .output()
            .ok()?;
        let stdout = String::from_utf8_lossy(&output.stdout);
        stdout.lines().next()
            .and_then(|line| line.strip_prefix("NVIM "))
            .map(|v| v.to_string())
    }
}

impl EditorBackend for NvimAdapter {
    fn name(&self) -> &str { "nvim" }

    fn info(&self) -> EditorBackendInfo {
        EditorBackendInfo {
            name: "nvim".into(),
            version: self.version.clone(),
            supports_lsp: true,
            supports_syntax: true,
        }
    }

    fn is_available(&self) -> bool {
        std::process::Command::new(&self.nvim_path)
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    fn read(&self, path: &str) -> Result<(String, usize), NexusError> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| NexusError::Io(format!("{path}: {e}")))?;
        let line_count = content.lines().count();
        Ok((content, line_count))
    }

    fn write(&self, path: &str, content: &str) -> Result<(), NexusError> {
        std::fs::write(path, content)
            .map_err(|e| NexusError::Io(format!("{path}: {e}")))
    }
}

// ---------------------------------------------------------------------------
// Buffer — per-file open state
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Buffer {
    pub path: String,
    pub name: String,
    pub content: String,
    pub modified: bool,
    pub line_count: usize,
    pub language: Option<String>,
    pub cursor_line: usize,
    pub cursor_col: usize,
}

// ---------------------------------------------------------------------------
// PaneBuffers — multiple open buffers per pane with active index
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
struct PaneBuffers {
    items: Vec<Buffer>,
    active: usize,
}

impl PaneBuffers {
    fn new() -> Self {
        Self {
            items: Vec::new(),
            active: 0,
        }
    }

    fn active_buffer(&self) -> Option<&Buffer> {
        self.items.get(self.active)
    }

    fn active_buffer_mut(&mut self) -> Option<&mut Buffer> {
        self.items.get_mut(self.active)
    }

    /// Find buffer by path, return its index.
    fn find_by_path(&self, path: &str) -> Option<usize> {
        self.items.iter().position(|b| b.path == path)
    }
}

// ---------------------------------------------------------------------------
// Orchestrator
// ---------------------------------------------------------------------------

pub struct Editor {
    backend: Box<dyn EditorBackend>,
    buffers: HashMap<String, PaneBuffers>, // keyed by pane_id
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EditorState {
    pub backend: EditorBackendInfo,
    pub open_buffers: Vec<BufferInfo>,
}

impl Editor {
    pub fn new() -> Self {
        Self {
            backend: Box::new(NativeAdapter),
            buffers: HashMap::new(),
        }
    }

    pub fn with_backend(backend: Box<dyn EditorBackend>) -> Self {
        Self {
            backend,
            buffers: HashMap::new(),
        }
    }

    pub fn set_backend(&mut self, backend: Box<dyn EditorBackend>) {
        self.backend = backend;
    }

    pub fn backend_name(&self) -> &str {
        self.backend.name()
    }

    pub fn backend_info(&self) -> EditorBackendInfo {
        self.backend.info()
    }

    /// Open a file in a pane. If already open, switches to it.
    /// Returns the buffer.
    pub fn open(&mut self, pane_id: &str, path: &str) -> Result<Buffer, NexusError> {
        let pane = self.buffers.entry(pane_id.to_string()).or_insert_with(PaneBuffers::new);

        // Already open? Switch to it.
        if let Some(idx) = pane.find_by_path(path) {
            pane.active = idx;
            return Ok(pane.items[idx].clone());
        }

        // Read from backend
        let (content, line_count) = self.backend.read(path)?;
        let name = path.rsplit('/').next().unwrap_or(path).to_string();
        let language = self.backend.detect_language(path);

        let buffer = Buffer {
            path: path.to_string(),
            name,
            content,
            modified: false,
            line_count,
            language,
            cursor_line: 0,
            cursor_col: 0,
        };

        pane.items.push(buffer.clone());
        pane.active = pane.items.len() - 1;
        Ok(buffer)
    }

    /// Get the active buffer for a pane.
    pub fn buffer(&self, pane_id: &str) -> Option<&Buffer> {
        self.buffers.get(pane_id)?.active_buffer()
    }

    /// Get all buffers for a pane.
    pub fn all_buffers(&self, pane_id: &str) -> Vec<&Buffer> {
        match self.buffers.get(pane_id) {
            Some(pane) => pane.items.iter().collect(),
            None => vec![],
        }
    }

    /// Update active buffer content (local edit, not yet saved).
    pub fn edit(&mut self, pane_id: &str, content: &str) -> Result<(), NexusError> {
        let pane = self.buffers.get_mut(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no buffers open in {pane_id}")))?;
        let buf = pane.active_buffer_mut()
            .ok_or_else(|| NexusError::NotFound(format!("no active buffer in {pane_id}")))?;
        buf.content = content.to_string();
        buf.line_count = content.lines().count();
        buf.modified = true;
        Ok(())
    }

    /// Save active buffer to disk via backend.
    pub fn save(&mut self, pane_id: &str) -> Result<(), NexusError> {
        let pane = self.buffers.get(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no buffers open in {pane_id}")))?;
        let buf = pane.active_buffer()
            .ok_or_else(|| NexusError::NotFound(format!("no active buffer in {pane_id}")))?;
        self.backend.write(&buf.path, &buf.content)?;
        // Mark clean
        let buf = self.buffers.get_mut(pane_id).unwrap().active_buffer_mut().unwrap();
        buf.modified = false;
        Ok(())
    }

    /// Close the active buffer. Returns true if pane still has buffers.
    pub fn close(&mut self, pane_id: &str) -> bool {
        let pane = match self.buffers.get_mut(pane_id) {
            Some(p) => p,
            None => return false,
        };

        if pane.items.is_empty() {
            self.buffers.remove(pane_id);
            return false;
        }

        pane.items.remove(pane.active);

        if pane.items.is_empty() {
            self.buffers.remove(pane_id);
            return false;
        }

        if pane.active >= pane.items.len() {
            pane.active = pane.items.len() - 1;
        }

        true
    }

    /// Full state for surfaces.
    pub fn state(&self) -> EditorState {
        let mut all_buffers = Vec::new();
        for pane in self.buffers.values() {
            for b in &pane.items {
                all_buffers.push(BufferInfo {
                    path: b.path.clone(),
                    name: b.name.clone(),
                    modified: b.modified,
                    line_count: b.line_count,
                    language: b.language.clone(),
                });
            }
        }
        EditorState {
            backend: self.backend.info(),
            open_buffers: all_buffers,
        }
    }
}

// ---------------------------------------------------------------------------
// TabProvider implementation
// ---------------------------------------------------------------------------

impl TabProvider for Editor {
    fn content_tabs(&self, pane_id: &str) -> Option<ContentTabState> {
        let pane = self.buffers.get(pane_id)?;
        if pane.items.is_empty() {
            return None;
        }
        Some(ContentTabState {
            tabs: pane.items.iter().map(|b| ContentTab {
                id: b.path.clone(),
                name: b.name.clone(),
                modified: b.modified,
                preview: false,
            }).collect(),
            active: pane.active,
        })
    }

    fn switch_content_tab(&mut self, pane_id: &str, index: usize) -> Result<ContentTabState, NexusError> {
        let pane = self.buffers.get_mut(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no buffers in {pane_id}")))?;
        if index >= pane.items.len() {
            return Err(NexusError::InvalidState(format!("index {index} out of range ({})", pane.items.len())));
        }
        pane.active = index;
        self.content_tabs(pane_id).ok_or_else(|| NexusError::Other("unreachable".into()))
    }

    fn close_content_tab(&mut self, pane_id: &str, index: usize) -> Result<Option<ContentTabState>, NexusError> {
        let pane = self.buffers.get_mut(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no buffers in {pane_id}")))?;
        if index >= pane.items.len() {
            return Err(NexusError::InvalidState(format!("index {index} out of range ({})", pane.items.len())));
        }
        pane.items.remove(index);
        if pane.items.is_empty() {
            self.buffers.remove(pane_id);
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

    fn setup_test_files() -> (tempfile::TempDir, String, String, String) {
        let dir = tempfile::tempdir().unwrap();
        let a = dir.path().join("a.rs");
        let b = dir.path().join("b.py");
        let c = dir.path().join("c.toml");
        std::fs::write(&a, "fn main() {}").unwrap();
        std::fs::write(&b, "print('hello')").unwrap();
        std::fs::write(&c, "[package]").unwrap();
        (
            dir,
            a.to_string_lossy().to_string(),
            b.to_string_lossy().to_string(),
            c.to_string_lossy().to_string(),
        )
    }

    #[test]
    fn native_read_write() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("test.rs");
        std::fs::write(&path, "fn main() {}\n").unwrap();

        let adapter = NativeAdapter;
        let (content, lines) = adapter.read(path.to_str().unwrap()).unwrap();
        assert!(content.contains("fn main"));
        assert_eq!(lines, 1);

        adapter.write(path.to_str().unwrap(), "fn main() { println!(\"hi\"); }\n").unwrap();
        let (content, _) = adapter.read(path.to_str().unwrap()).unwrap();
        assert!(content.contains("println"));
    }

    #[test]
    fn native_read_missing_errors() {
        let adapter = NativeAdapter;
        assert!(adapter.read("/nonexistent/file.txt").is_err());
    }

    #[test]
    fn language_detection() {
        let adapter = NativeAdapter;
        assert_eq!(adapter.detect_language("main.rs"), Some("rust".into()));
        assert_eq!(adapter.detect_language("app.tsx"), Some("typescript".into()));
        assert_eq!(adapter.detect_language("Cargo.toml"), Some("toml".into()));
        assert_eq!(adapter.detect_language("noext"), None);
    }

    #[test]
    fn multi_buffer_open_and_switch() {
        let (_dir, a, b, _c) = setup_test_files();
        let mut editor = Editor::new();

        // Open first file
        let buf = editor.open("p1", &a).unwrap();
        assert_eq!(buf.name, "a.rs");
        assert_eq!(buf.language, Some("rust".into()));

        // Open second file
        let buf = editor.open("p1", &b).unwrap();
        assert_eq!(buf.name, "b.py");

        // Active should be the second file
        assert_eq!(editor.buffer("p1").unwrap().name, "b.py");

        // Content tabs should show both
        let tabs = editor.content_tabs("p1").unwrap();
        assert_eq!(tabs.tabs.len(), 2);
        assert_eq!(tabs.active, 1);
        assert_eq!(tabs.tabs[0].name, "a.rs");
        assert_eq!(tabs.tabs[1].name, "b.py");
    }

    #[test]
    fn open_same_file_switches() {
        let (_dir, a, b, _c) = setup_test_files();
        let mut editor = Editor::new();

        editor.open("p1", &a).unwrap();
        editor.open("p1", &b).unwrap();
        assert_eq!(editor.buffer("p1").unwrap().name, "b.py");

        // Open a.rs again — should switch, not duplicate
        editor.open("p1", &a).unwrap();
        assert_eq!(editor.buffer("p1").unwrap().name, "a.rs");

        let tabs = editor.content_tabs("p1").unwrap();
        assert_eq!(tabs.tabs.len(), 2); // still 2, not 3
        assert_eq!(tabs.active, 0);
    }

    #[test]
    fn switch_content_tab() {
        let (_dir, a, b, c) = setup_test_files();
        let mut editor = Editor::new();

        editor.open("p1", &a).unwrap();
        editor.open("p1", &b).unwrap();
        editor.open("p1", &c).unwrap();

        // Switch to first
        let state = editor.switch_content_tab("p1", 0).unwrap();
        assert_eq!(state.active, 0);
        assert_eq!(editor.buffer("p1").unwrap().name, "a.rs");

        // Switch to middle
        let state = editor.switch_content_tab("p1", 1).unwrap();
        assert_eq!(state.active, 1);
        assert_eq!(editor.buffer("p1").unwrap().name, "b.py");

        // Out of range
        assert!(editor.switch_content_tab("p1", 5).is_err());
    }

    #[test]
    fn close_content_tab() {
        let (_dir, a, b, c) = setup_test_files();
        let mut editor = Editor::new();

        editor.open("p1", &a).unwrap();
        editor.open("p1", &b).unwrap();
        editor.open("p1", &c).unwrap();

        // Close middle (b.py, index 1). Active was 2 (c.toml).
        editor.switch_content_tab("p1", 2).unwrap();
        let state = editor.close_content_tab("p1", 1).unwrap().unwrap();
        assert_eq!(state.tabs.len(), 2);
        // Active should shift down since we removed before it
        assert_eq!(state.active, 1);
        assert_eq!(state.tabs[0].name, "a.rs");
        assert_eq!(state.tabs[1].name, "c.toml");

        // Close all
        editor.close_content_tab("p1", 0).unwrap();
        let result = editor.close_content_tab("p1", 0).unwrap();
        assert!(result.is_none()); // no tabs remain
    }

    #[test]
    fn edit_and_save_active_buffer() {
        let (_dir, a, b, _c) = setup_test_files();
        let mut editor = Editor::new();

        editor.open("p1", &a).unwrap();
        editor.open("p1", &b).unwrap();

        // Edit active (b.py)
        editor.edit("p1", "print('world')").unwrap();
        assert!(editor.buffer("p1").unwrap().modified);

        // a.rs should be unmodified
        editor.switch_content_tab("p1", 0).unwrap();
        assert!(!editor.buffer("p1").unwrap().modified);

        // Switch back and save
        editor.switch_content_tab("p1", 1).unwrap();
        editor.save("p1").unwrap();
        assert!(!editor.buffer("p1").unwrap().modified);

        // Verify on disk
        let saved = std::fs::read_to_string(&b).unwrap();
        assert!(saved.contains("world"));
    }

    #[test]
    fn close_removes_active_returns_has_more() {
        let (_dir, a, b, _c) = setup_test_files();
        let mut editor = Editor::new();

        editor.open("p1", &a).unwrap();
        editor.open("p1", &b).unwrap();

        // Close active (b.py) via old close() method
        let has_more = editor.close("p1");
        assert!(has_more);
        assert_eq!(editor.buffer("p1").unwrap().name, "a.rs");

        // Close last
        let has_more = editor.close("p1");
        assert!(!has_more);
        assert!(editor.buffer("p1").is_none());
    }

    #[test]
    fn backend_swappable() {
        struct MockEditor;
        impl EditorBackend for MockEditor {
            fn name(&self) -> &str { "nvim" }
            fn info(&self) -> EditorBackendInfo {
                EditorBackendInfo { name: "nvim".into(), version: Some("0.10".into()), supports_lsp: true, supports_syntax: true }
            }
            fn is_available(&self) -> bool { true }
            fn read(&self, _path: &str) -> Result<(String, usize), NexusError> {
                Ok(("mock content".into(), 1))
            }
            fn write(&self, _path: &str, _content: &str) -> Result<(), NexusError> { Ok(()) }
        }

        let mut editor = Editor::new();
        assert_eq!(editor.backend_name(), "native");

        editor.set_backend(Box::new(MockEditor));
        assert_eq!(editor.backend_name(), "nvim");
        assert!(editor.backend_info().supports_lsp);
    }

    #[test]
    fn state_tracks_all_buffers() {
        let (_dir, a, b, _c) = setup_test_files();
        let mut editor = Editor::new();
        editor.open("p1", &a).unwrap();
        editor.open("p1", &b).unwrap();
        editor.open("p2", &a).unwrap();

        let state = editor.state();
        assert_eq!(state.open_buffers.len(), 3); // 2 in p1 + 1 in p2
        assert_eq!(state.backend.name, "native");
    }

    #[test]
    fn supports_content_tabs_true() {
        let editor = Editor::new();
        assert!(editor.supports_content_tabs());
    }

    #[test]
    fn content_tabs_empty_pane_returns_none() {
        let editor = Editor::new();
        assert!(editor.content_tabs("nonexistent").is_none());
    }

    #[test]
    fn modified_shows_in_content_tabs() {
        let (_dir, a, _b, _c) = setup_test_files();
        let mut editor = Editor::new();
        editor.open("p1", &a).unwrap();

        let tabs = editor.content_tabs("p1").unwrap();
        assert!(!tabs.tabs[0].modified);

        editor.edit("p1", "changed").unwrap();

        let tabs = editor.content_tabs("p1").unwrap();
        assert!(tabs.tabs[0].modified);
    }
}
