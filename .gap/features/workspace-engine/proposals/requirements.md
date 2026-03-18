# Requirements: Multi-Folder Workspace Engine

## Functional Requirements
1.  **Workspace Loading**: `nxs load <file.nxs-workspace>` must parse the JSON and initialize the session with the specified roots.
2.  **Aggregate Search**: The search core (`core/engine/search/live_grep.sh` and `quick_find.sh`) must be updated to accept multiple paths.
3.  **Dynamic Scoping**: Users should be able to toggle "Current Folder Only" vs "Whole Workspace" search during runtime.
4.  **LSP Multi-Client**: The Daemon Manager must trigger multiple instances of relevant LSPs for each project root detected.
5.  **Status Line Integration**: The HUD must display which workspace is active.

## Technical Requirements
- **JSON Format**: Use `jq` for robust parsing of the `.nxs-workspace` files.
- **Path Resolution**: Must handle absolute and project-relative paths.
- **Conflict Handling**: Behavior when two folders have the same name must be defined (e.g., use parent directory as prefix).

## Non-Functional Requirements
- **Low Overhead**: Adding a folder should not linearly increase background CPU usage (staggered LSP starts).
- **Indestructibility**: If one root is deleted/moved, the workspace should still load the others.
