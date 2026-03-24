//! Nexus Engine — surface-agnostic workspace orchestration.
//!
//! This crate provides the core engine for Nexus Shell. It manages
//! workspaces, tab stacks, event routing, and composition layouts
//! through an abstract Surface trait.
//!
//! # Architecture
//!
//! ```text
//! NexusCore (facade)
//! ├── Surface trait     (display abstraction)
//! ├── StackManager      (tab stack state)
//! └── EventBus          (typed pub/sub)
//! ```

pub mod bus;
pub mod core;
pub mod stack;
pub mod stack_manager;
pub mod surface;

// Re-exports for convenience
pub use crate::core::NexusCore;
pub use bus::{EventBus, EventType, TypedEvent};
pub use stack::{Tab, TabStack, TabStatus};
pub use stack_manager::StackManager;
pub use surface::{
    ContainerInfo, Dimensions, Geometry, HudModule, MenuItem, NullSurface, SplitDirection, Surface,
};
