//! Daemon auto-start logic — find and launch nexus-daemon if no socket exists.

use nexus_core::NexusError;
use std::path::{Path, PathBuf};

/// Locate the nexus-daemon binary.
pub fn find_daemon_bin() -> Result<PathBuf, NexusError> {
    // 1. NEXUS_DAEMON_BIN env var
    if let Ok(path) = std::env::var("NEXUS_DAEMON_BIN") {
        let p = PathBuf::from(&path);
        if p.is_file() {
            return Ok(p);
        }
    }
    // 2. Sibling of current executable
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let sibling = parent.join("nexus-daemon");
            if sibling.is_file() {
                return Ok(sibling);
            }
        }
    }
    // 3. PATH lookup
    let path_var = std::env::var("PATH").unwrap_or_default();
    for dir in std::env::split_paths(&path_var) {
        let candidate = dir.join("nexus-daemon");
        if candidate.is_file() {
            return Ok(candidate);
        }
    }
    Err(NexusError::NotFound("nexus-daemon binary not found".into()))
}

/// Spawn the daemon and wait for the socket to appear.
pub fn auto_launch(socket_path: &Path) -> Result<(), NexusError> {
    let daemon_bin = find_daemon_bin()?;

    std::process::Command::new(&daemon_bin)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .map_err(|e| NexusError::Protocol(format!("failed to spawn daemon: {e}")))?;

    // Poll for socket (50ms * 60 = 3s)
    for _ in 0..60 {
        if socket_path.exists() {
            return Ok(());
        }
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
    Err(NexusError::Protocol("daemon failed to start within 3s".into()))
}
