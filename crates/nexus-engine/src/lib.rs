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

pub mod browser;
pub mod bus;
pub mod chat;
pub mod content_tabs;
pub mod core;
pub mod dispatch;
pub mod editor;
pub mod explorer;
pub mod layout;
pub mod info;
pub mod menu;
pub mod richtext;
pub mod hud;
pub mod terminal;
pub mod pty;
pub mod registry;
pub mod stack;
pub mod stack_manager;
pub mod persistence;
pub mod surface;
pub mod templates;

// Re-exports for convenience
pub use crate::core::{DisplaySettings, NexusCore};
pub use chat::{Chat, ChatBackend, ChatMessage, Conversation};
pub use editor::{Editor, EditorBackend, NvimAdapter, Buffer, EditorState};
pub use explorer::{Explorer, ExplorerBackend, BrootAdapter, ExplorerEntry, ExplorerState};
pub use menu::{MenuEngine, MenuItem, MenuList};
pub use terminal::{Terminal, TerminalBackend, TerminalSession};
pub use persistence::{WorkspaceSave, LayoutExport, PaneState};
pub use content_tabs::{ContentTab, ContentTabState, TabProvider};
pub use dispatch::dispatch;
pub use registry::CapabilityRegistry;
pub use bus::{EventBus, EventType, TypedEvent};
pub use layout::{Direction, LayoutNode, LayoutTree, Nav};
pub use stack::{Tab, TabStack, TabStatus};
pub use pty::PtyManager;
pub use stack_manager::StackManager;
pub use surface::{
    ContainerInfo, Dimensions, Geometry, HudModule, MenuItem as SurfaceMenuItem, Mux, NullMux, SplitDirection,
};
