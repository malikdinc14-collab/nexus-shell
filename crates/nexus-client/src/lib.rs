//! Nexus client library — sync JSON-RPC 2.0 client for the Nexus daemon.
//!
//! Provides `NexusClient` (command connection) and `EventSubscription`
//! (filtered event stream). Surfaces (CLI, Tauri, tmux) depend on this
//! crate — never on the engine directly.

pub mod auto_launch;
pub mod client;
pub mod events;
pub mod protocol;

pub use client::NexusClient;
pub use events::EventSubscription;
pub use protocol::{JsonRpcError, JsonRpcNotification, JsonRpcRequest, JsonRpcResponse};
