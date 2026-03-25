//! Nexus daemon — shared NexusCore over unix socket.
//!
//! Surfaces (tauri, cli, tmux) connect to the daemon instead of
//! embedding NexusCore in-process, enabling shared state.

pub mod client;
pub mod event_bridge;
pub mod protocol;
pub mod server;
