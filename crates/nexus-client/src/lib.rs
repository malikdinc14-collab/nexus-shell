//! Nexus client library — sync JSON-RPC 2.0 client for the Nexus daemon.
//!
//! Provides `NexusClient` (command connection) and `EventSubscription`
//! (filtered event stream). Surfaces (CLI, Tauri, tmux) depend on this
//! crate — never on the engine directly.

pub mod protocol;
