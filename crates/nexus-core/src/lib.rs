//! Nexus Core — shared types, traits, and constants for all Nexus crates.

pub mod config;
pub mod constants;
pub mod error;
// pub mod mux — added in Task 2 once mux.rs exists

pub use config::NexusConfig;
// socket_path is defined for all targets (unix + not(unix) stubs); all target branches must define it.
pub use constants::{socket_path, DEFAULT_SESSION_NAME};
pub use error::NexusError;
