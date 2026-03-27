//! FileRouter — maps file extensions to modules.
//! Central decision point for "open this file" from any entry point.

use std::collections::HashMap;
use std::path::Path;

/// Which module should handle a file.
#[derive(Debug, Clone, PartialEq)]
pub enum FileTarget {
    Editor,
    RichText,
    Browser,
    // Future: ImageViewer, PdfViewer, etc.
}

impl FileTarget {
    /// The tab/module name used by the stack system.
    pub fn module_name(&self) -> &'static str {
        match self {
            FileTarget::Editor => "Editor",
            FileTarget::RichText => "RichText",
            FileTarget::Browser => "Browser",
        }
    }

    /// The dispatch domain for opening files in this module.
    pub fn open_command(&self) -> &'static str {
        match self {
            FileTarget::Editor => "editor.open",
            FileTarget::RichText => "markdown.open",
            FileTarget::Browser => "browser.open",
        }
    }
}

pub struct FileRouter {
    ext_map: HashMap<String, FileTarget>,
}

impl FileRouter {
    pub fn new() -> Self {
        let mut ext_map = HashMap::new();

        // Markdown → RichText
        for ext in &["md", "mdx", "markdown"] {
            ext_map.insert(ext.to_string(), FileTarget::RichText);
        }

        // Web → Browser
        for ext in &["html", "htm", "svg"] {
            ext_map.insert(ext.to_string(), FileTarget::Browser);
        }

        // Everything else falls through to Editor (default)

        Self { ext_map }
    }

    /// Determine which module should open a given file path.
    pub fn route(&self, path: &str) -> FileTarget {
        Path::new(path)
            .extension()
            .and_then(|ext| ext.to_str())
            .and_then(|ext| self.ext_map.get(&ext.to_lowercase()))
            .cloned()
            .unwrap_or(FileTarget::Editor)
    }
}

impl Default for FileRouter {
    fn default() -> Self {
        Self::new()
    }
}
