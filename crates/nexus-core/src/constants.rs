//! Shared constants and runtime paths.

use std::path::PathBuf;

/// Default session name when no name is specified.
pub const DEFAULT_SESSION_NAME: &str = "nexus";

/// Compute the unix socket path.
///
/// Resolution order:
///   1. `$XDG_RUNTIME_DIR/nexus/nexus.sock`
///   2. `/tmp/nexus-<uid>/nexus.sock`
#[cfg(unix)]
pub fn socket_path() -> PathBuf {
    if let Ok(runtime_dir) = std::env::var("XDG_RUNTIME_DIR") {
        std::path::Path::new(&runtime_dir)
            .join("nexus")
            .join("nexus.sock")
    } else {
        // SAFETY: getuid(3) is always safe to call; it has no preconditions and cannot fail.
        let uid = unsafe { libc::getuid() };
        PathBuf::from(format!("/tmp/nexus-{uid}/nexus.sock"))
    }
}

#[cfg(not(unix))]
pub fn socket_path() -> PathBuf {
    PathBuf::from(r"\\.\pipe\nexus")
}

/// Compute the event socket path (sibling of command socket).
#[cfg(unix)]
pub fn events_socket_path() -> PathBuf {
    let mut p = socket_path();
    p.set_file_name("nexus-events.sock");
    p
}

#[cfg(not(unix))]
pub fn events_socket_path() -> PathBuf {
    PathBuf::from(r"\\.\pipe\nexus-events")
}

/// Compute the PID file path (sibling of command socket).
#[cfg(unix)]
pub fn pid_path() -> PathBuf {
    let mut p = socket_path();
    p.set_file_name("nexus.pid");
    p
}

#[cfg(not(unix))]
pub fn pid_path() -> PathBuf {
    PathBuf::from(r"\\.\pipe\nexus.pid")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(unix)]
    #[test]
    fn socket_path_returns_a_path() {
        let p = socket_path();
        assert_eq!(p.file_name().unwrap(), "nexus.sock");
    }

    #[test]
    fn default_session_name_non_empty() {
        assert!(!DEFAULT_SESSION_NAME.is_empty());
    }

    #[cfg(unix)]
    #[test]
    fn events_socket_path_returns_events_sock() {
        let p = events_socket_path();
        assert_eq!(p.file_name().unwrap(), "nexus-events.sock");
        // Same parent directory as command socket
        assert_eq!(p.parent(), socket_path().parent());
    }

    #[cfg(unix)]
    #[test]
    fn pid_path_returns_pid_file() {
        let p = pid_path();
        assert_eq!(p.file_name().unwrap(), "nexus.pid");
        assert_eq!(p.parent(), socket_path().parent());
    }
}
