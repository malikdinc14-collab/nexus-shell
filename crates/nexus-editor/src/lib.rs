//! EditorBackend trait — abstraction over editor processes.
//!
//! Implementations: NullEditor (no-op), NvimEditor (Phase 4).

use nexus_core::NexusError;

/// Abstract interface for editor backends (nvim, helix, kakoune, etc.).
///
/// An EditorBackend manages a single editor session attached to a pane.
/// The engine calls these methods; the backend handles process lifecycle.
pub trait EditorBackend: Send {
    /// Open a file at the given cursor position. Must be idempotent.
    fn open(&mut self, path: &str, line: u32, col: u32) -> Result<(), NexusError>;

    /// Close the editor session and release resources.
    fn close(&mut self) -> Result<(), NexusError>;

    /// Send raw input to the editor (key sequences, commands).
    fn send_input(&mut self, input: &str) -> Result<(), NexusError>;

    /// Resize the editor viewport.
    fn resize(&mut self, cols: u16, rows: u16) -> Result<(), NexusError>;

    /// Return true if the editor process is alive.
    fn is_alive(&self) -> bool;
}

/// No-op editor for testing and headless operation.
pub struct NullEditor;

impl EditorBackend for NullEditor {
    fn open(&mut self, _path: &str, _line: u32, _col: u32) -> Result<(), NexusError> {
        Ok(())
    }

    fn close(&mut self) -> Result<(), NexusError> {
        Ok(())
    }

    fn send_input(&mut self, _input: &str) -> Result<(), NexusError> {
        Ok(())
    }

    fn resize(&mut self, _cols: u16, _rows: u16) -> Result<(), NexusError> {
        Ok(())
    }

    fn is_alive(&self) -> bool {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn null_editor_open_returns_ok() {
        let mut ed = NullEditor;
        assert!(ed.open("/tmp/foo.rs", 0, 0).is_ok());
    }

    #[test]
    fn null_editor_close_returns_ok() {
        let mut ed = NullEditor;
        assert!(ed.close().is_ok());
    }

    #[test]
    fn null_editor_is_alive_false() {
        let ed = NullEditor;
        assert!(!ed.is_alive());
    }

    #[test]
    fn null_editor_is_send() {
        fn assert_send<T: Send>() {}
        assert_send::<NullEditor>();
    }

    #[test]
    fn null_editor_send_input_ok() {
        let mut ed = NullEditor;
        assert!(ed.send_input(":w\n").is_ok());
    }

    #[test]
    fn null_editor_resize_ok() {
        let mut ed = NullEditor;
        assert!(ed.resize(80, 24).is_ok());
    }
}
