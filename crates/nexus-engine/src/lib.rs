//! Nexus Engine — mux-agnostic workspace orchestration.
//!
//! This crate provides the core engine for Nexus Shell. It manages
//! workspaces, tab stacks, event routing, and composition layouts
//! through an abstract Mux trait.
//!
//! # Architecture
//!
//! ```text
//! NexusCore (facade)
//! ├── Mux trait         (multiplexer abstraction)
//! ├── StackManager      (tab stack state)
//! └── EventBus          (typed pub/sub)
//! ```

pub mod bus;
pub mod core;
pub mod dispatch;
pub mod layout;
pub mod pty;
pub mod registry;
pub mod stack;
pub mod stack_manager;
pub mod surface;

// Re-exports for convenience
pub use crate::core::NexusCore;
pub use dispatch::dispatch;
pub use registry::CapabilityRegistry;
pub use bus::{EventBus, EventType, TypedEvent};
pub use layout::{Direction, LayoutNode, LayoutTree, Nav, PaneType};
pub use stack::{Tab, TabStack, TabStatus};
pub use pty::PtyManager;
pub use stack_manager::StackManager;
pub use surface::{
    ContainerInfo, Dimensions, Geometry, HudModule, MenuItem, Mux, NullMux, SplitDirection,
};
