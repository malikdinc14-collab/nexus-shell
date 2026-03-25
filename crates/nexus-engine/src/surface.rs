//! Re-export Mux types from nexus-core.
//!
//! All Mux-related types now live in nexus-core::mux so that adapter
//! crates (nexus-tmux, etc.) can depend on the trait without pulling
//! in the full engine.
pub use nexus_core::mux::*;
