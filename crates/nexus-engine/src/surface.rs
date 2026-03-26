//! Re-export Mux and Surface types from nexus-core.
//!
//! All Mux-related types now live in nexus-core::mux so that adapter
//! crates (nexus-tmux, etc.) can depend on the trait without pulling
//! in the full engine. Surface types live in nexus-core::surface.
pub use nexus_core::mux::{
    ContainerInfo, Dimensions, Geometry, HudModule, MenuItem,
    Mux, NullMux, SplitDirection,
};
pub use nexus_core::surface::{
    SurfaceCapabilities, SurfaceMode, SurfaceRegistration, SurfaceRegistry,
};
