# Requirements: Headless DAP

## Functional Requirements
1.  **Language Support**: Initial support for Python (debugpy) and Node.js.
2.  **State Persistence**: The debugger must continue running even if the user switches Tmux windows or layouts.
3.  **Unified Control**: A single command (e.g., `:debug`) to start/attach/terminate sessions.
4.  **Logging**: All debug output must be piped to a dedicated, scrollable Tmux pane.

## Technical Requirements
- **DAP Core**: Interface with existing DAP servers via common JSON-RPC.
- **Tmux Integration**: Reserve Slot 9 for the "Debug Console".
- **IPC**: Use `/tmp/nexus_dap_$(whoami).pipe` for communication between the editor and the background debugger.

## Non-Functional Requirements
- **Stability**: Crashing the debugger should NOT crash the IDE or the editor.
- **Security**: Debuggers must be confined to the active workspace roots.
