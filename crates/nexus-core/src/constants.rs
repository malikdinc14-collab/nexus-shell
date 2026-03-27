//! Shared constants and runtime paths.

use std::path::PathBuf;

/// Default session name when no name is specified.
pub const DEFAULT_SESSION_NAME: &str = "nexus";

/// Returns the TCP address for the command socket.
pub fn cmd_addr() -> std::net::SocketAddr {
    let port = std::env::var("NEXUS_CMD_PORT")
        .unwrap_or_else(|_| "7723".to_string())
        .parse()
        .unwrap_or(7723);
    std::net::SocketAddr::new(std::net::IpAddr::V4(std::net::Ipv4Addr::new(127, 0, 0, 1)), port)
}

/// Returns the TCP address for the event socket.
pub fn event_addr() -> std::net::SocketAddr {
    let port = std::env::var("NEXUS_EVENT_PORT")
        .unwrap_or_else(|_| "7724".to_string())
        .parse()
        .unwrap_or(7724);
    std::net::SocketAddr::new(std::net::IpAddr::V4(std::net::Ipv4Addr::new(127, 0, 0, 1)), port)
}

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
    if let Ok(appdata) = std::env::var("APPDATA") {
        std::path::Path::new(&appdata).join("nexus").join("nexus.pid")
    } else {
        PathBuf::from(r"C:\nexus\nexus.pid")
    }
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
