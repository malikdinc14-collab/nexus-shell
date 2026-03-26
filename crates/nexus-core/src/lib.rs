//! Nexus Core — shared types, traits, and constants for all Nexus crates.

pub mod adapters;
pub mod capability;
pub mod config;
pub mod constants;
pub mod error;
pub mod keymap;
pub mod mux;
pub mod surface;

pub use adapters::{ClaudeAdapter, FsExplorer, NotesAdapter, SystemInfoAdapter, TauriBrowserAdapter};
pub use capability::{
    AdapterManifest, Capability, CapabilityType, ChatCapability, ChatEvent, DirEntry as CapabilityDirEntry,
    EditorCapability, ExplorerCapability, SystemContext, BrowserCapability, NoteNode, RichTextCapability,
    HUDCapability, HUDFrame, HUDPart,
};
pub use config::NexusConfig;
pub use constants::{socket_path, DEFAULT_SESSION_NAME};
pub use error::NexusError;
pub use keymap::{CommandEntry, KeyBinding};
pub use mux::{
    ContainerInfo, Dimensions, Geometry, HudModule, MenuItem, Mux, NullMux, SplitDirection,
};
pub use surface::{SurfaceCapabilities, SurfaceMode, SurfaceRegistration, SurfaceRegistry};
