//! Nexus Core — shared types, traits, and constants for all Nexus crates.

pub mod capability;
pub mod config;
pub mod constants;
pub mod error;
pub mod keymap;
pub mod mux;

pub use capability::{
    AdapterManifest, Capability, CapabilityType, ChatCapability, ChatEvent, DirEntry as CapabilityDirEntry,
    EditorCapability, ExplorerCapability, SystemContext,
};
pub use config::NexusConfig;
// socket_path is defined for all targets (unix + not(unix) stubs); all target branches must define it.
pub use constants::{socket_path, DEFAULT_SESSION_NAME};
pub use error::NexusError;
pub use keymap::{CommandEntry, KeyBinding};
pub use mux::{
    ContainerInfo, Dimensions, Geometry, HudModule, MenuItem, Mux, NullMux, SplitDirection,
};
