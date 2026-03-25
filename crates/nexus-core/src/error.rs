//! Unified error type for all Nexus crates.

use std::fmt;

#[derive(Debug, Clone, PartialEq)]
pub enum NexusError {
    /// Operation on a pane/container that does not exist.
    NotFound(String),
    /// An operation was attempted in an invalid state.
    InvalidState(String),
    /// I/O error (socket, filesystem).
    Io(String),
    /// Protocol/serialization error.
    Protocol(String),
    /// Generic error with message.
    Other(String),
}

impl fmt::Display for NexusError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NexusError::NotFound(s) => write!(f, "not found: {s}"),
            NexusError::InvalidState(s) => write!(f, "invalid state: {s}"),
            NexusError::Io(s) => write!(f, "io error: {s}"),
            NexusError::Protocol(s) => write!(f, "protocol error: {s}"),
            NexusError::Other(s) => write!(f, "{s}"),
        }
    }
}

impl std::error::Error for NexusError {}

impl From<std::io::Error> for NexusError {
    fn from(e: std::io::Error) -> Self {
        NexusError::Io(e.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn display_not_found() {
        let e = NexusError::NotFound("pane-1".into());
        assert_eq!(e.to_string(), "not found: pane-1");
    }

    #[test]
    fn from_io_error() {
        let io = std::io::Error::new(std::io::ErrorKind::NotFound, "file missing");
        let e = NexusError::from(io);
        assert!(matches!(e, NexusError::Io(_)));
    }
}
