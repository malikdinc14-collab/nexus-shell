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
}
