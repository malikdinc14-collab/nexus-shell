//! Nexus daemon — shared NexusCore over unix socket.
//!
//! Surfaces (tauri, cli, tmux) connect to the daemon instead of
//! embedding NexusCore in-process, enabling shared state.

pub mod event_bridge;
pub mod server;
