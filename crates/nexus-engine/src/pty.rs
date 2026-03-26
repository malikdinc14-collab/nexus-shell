//! PTY manager -- spawn and manage pseudo-terminal sessions.
//!
//! Each terminal pane gets a PTY identified by its pane ID.
//! A background thread reads PTY output and publishes events through the EventBus.

use portable_pty::{native_pty_system, CommandBuilder, MasterPty, PtySize};
use std::collections::HashMap;
use std::io::{Read, Write};
use std::sync::{Arc, Mutex};
use std::thread;

use nexus_core::NexusError;

use crate::bus::{EventBus, EventType, TypedEvent};

/// A single PTY session.
pub(crate) struct PtySession {
    master: Box<dyn MasterPty + Send>,
    writer: Box<dyn Write + Send>,
    /// Handle to the reader thread (exits on EOF or error).
    _reader_thread: thread::JoinHandle<()>,
}

/// Manages all PTY sessions, keyed by pane ID.
pub struct PtyManager {
    pub(crate) sessions: HashMap<String, PtySession>,
}

impl PtyManager {
    pub fn new() -> Self {
        Self {
            sessions: HashMap::new(),
        }
    }

    /// Spawn a new PTY for a pane running the user's $SHELL.
    pub fn spawn(
        &mut self,
        pane_id: &str,
        cwd: &str,
        bus: Arc<Mutex<EventBus>>,
    ) -> Result<(), NexusError> {
        let shell = std::env::var("SHELL").unwrap_or_else(|_| "/bin/zsh".into());
        self.spawn_cmd(pane_id, cwd, &shell, &[], bus)
    }

    /// Spawn a PTY running a specific command with args.
    ///
    /// Idempotent: returns `Ok(())` if a session already exists for `pane_id`.
    pub fn spawn_cmd(
        &mut self,
        pane_id: &str,
        cwd: &str,
        program: &str,
        args: &[String],
        bus: Arc<Mutex<EventBus>>,
    ) -> Result<(), NexusError> {
        if self.sessions.contains_key(pane_id) {
            return Ok(()); // Idempotent
        }

        let pty_system = native_pty_system();
        let pair = pty_system
            .openpty(PtySize {
                rows: 24,
                cols: 80,
                pixel_width: 0,
                pixel_height: 0,
            })
            .map_err(|e| NexusError::Io(e.to_string()))?;

        let mut cmd = CommandBuilder::new(program);
        for arg in args {
            cmd.arg(arg);
        }
        cmd.cwd(cwd);

        let _child = pair
            .slave
            .spawn_command(cmd)
            .map_err(|e| NexusError::Io(e.to_string()))?;

        // Drop slave side -- we only need the master
        drop(pair.slave);

        let writer = pair
            .master
            .take_writer()
            .map_err(|e| NexusError::Io(e.to_string()))?;

        let mut reader = pair
            .master
            .try_clone_reader()
            .map_err(|e| NexusError::Io(e.to_string()))?;

        let id = pane_id.to_string();
        let reader_thread = thread::spawn(move || {
            let mut buf = [0u8; 4096];
            loop {
                match reader.read(&mut buf) {
                    Ok(0) => {
                        // PTY closed
                        let event = TypedEvent::new(EventType::Custom, "pty.exit")
                            .with_payload("paneId", id.as_str());
                        if let Ok(mut b) = bus.lock() {
                            b.publish(event);
                        }
                        break;
                    }
                    Ok(n) => {
                        let data: Vec<u8> = buf[..n].to_vec();
                        let event = TypedEvent::new(EventType::Custom, "pty.output")
                            .with_payload("paneId", id.as_str())
                            .with_payload("data", serde_json::json!(data));
                        if let Ok(mut b) = bus.lock() {
                            b.publish(event);
                        }
                    }
                    Err(_) => break,
                }
            }
        });

        self.sessions.insert(
            pane_id.to_string(),
            PtySession {
                master: pair.master,
                writer,
                _reader_thread: reader_thread,
            },
        );

        Ok(())
    }

    /// Write data to a PTY (user keyboard input).
    pub fn write(&mut self, pane_id: &str, data: &str) -> Result<(), NexusError> {
        let session = self
            .sessions
            .get_mut(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no PTY for {pane_id}")))?;
        session
            .writer
            .write_all(data.as_bytes())
            .map_err(|e| NexusError::Io(e.to_string()))?;
        session.writer.flush().map_err(|e| NexusError::Io(e.to_string()))?;
        Ok(())
    }

    /// Resize a PTY.
    pub fn resize(&mut self, pane_id: &str, cols: u16, rows: u16) -> Result<(), NexusError> {
        let session = self
            .sessions
            .get(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no PTY for {pane_id}")))?;
        session
            .master
            .resize(PtySize {
                rows,
                cols,
                pixel_width: 0,
                pixel_height: 0,
            })
            .map_err(|e| NexusError::Io(e.to_string()))?;
        Ok(())
    }

    /// Number of active PTY sessions.
    pub fn active_count(&self) -> usize {
        self.sessions.len()
    }

    /// Kill a PTY session. Dropping master/writer closes the PTY.
    pub fn kill(&mut self, pane_id: &str) -> Result<(), NexusError> {
        self.sessions
            .remove(pane_id)
            .ok_or_else(|| NexusError::NotFound(format!("no PTY for {pane_id}")))?;
        Ok(())
    }
}

impl Default for PtyManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn active_count_starts_at_zero() {
        let mgr = PtyManager::new();
        assert_eq!(mgr.active_count(), 0);
    }

    #[test]
    fn pty_manager_new() {
        let mgr = PtyManager::new();
        assert!(mgr.sessions.is_empty());
    }

    #[test]
    fn pty_manager_write_nonexistent_errors() {
        let mut mgr = PtyManager::new();
        assert!(mgr.write("nonexistent", "hello").is_err());
    }

    #[test]
    fn pty_manager_resize_nonexistent_errors() {
        let mut mgr = PtyManager::new();
        assert!(mgr.resize("nonexistent", 80, 24).is_err());
    }

    #[test]
    fn pty_manager_kill_nonexistent_errors() {
        let mut mgr = PtyManager::new();
        assert!(mgr.kill("nonexistent").is_err());
    }

    #[test]
    fn pty_manager_spawn_creates_session() {
        let bus = Arc::new(Mutex::new(crate::bus::EventBus::new()));
        let mut mgr = PtyManager::new();
        let result = mgr.spawn("test-pane", "/tmp", bus);
        assert!(result.is_ok());
        assert!(mgr.sessions.contains_key("test-pane"));
        let _ = mgr.kill("test-pane");
    }

    #[test]
    fn pty_manager_spawn_idempotent() {
        let bus = Arc::new(Mutex::new(crate::bus::EventBus::new()));
        let mut mgr = PtyManager::new();
        let _ = mgr.spawn("test-pane", "/tmp", bus.clone());
        let result = mgr.spawn("test-pane", "/tmp", bus);
        assert!(result.is_ok());
        let _ = mgr.kill("test-pane");
    }
}
