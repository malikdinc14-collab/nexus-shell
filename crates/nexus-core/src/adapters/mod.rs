pub mod claude;
pub mod fs_explorer;
pub mod notes_adapter;
pub mod system_info;
pub mod tauri_browser;

pub use claude::ClaudeAdapter;
pub use fs_explorer::FsExplorer;
pub use notes_adapter::NotesAdapter;
pub use system_info::SystemInfoAdapter;
pub use tauri_browser::TauriBrowserAdapter;
