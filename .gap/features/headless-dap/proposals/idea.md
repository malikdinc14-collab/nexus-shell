# Idea: Headless DAP (Debug Adapter Protocol)

## Problem Statement
Debugging usually requires a heavy IDE or a locked terminal session. If the user swaps compositions or panes, the debugger state is often lost or hidden.

## Proposed Solution
Decouple the Debugger from the Buffer. The Debug Adapter runs as a background daemon (Headless), while Tmux provides a "Debug Console" pane that persists across layout changes.

## Key Features
- **DAP Daemon**: A background service that manages the debug session (Python, Node, GDB).
- **Sticky Debug Pane**: A dedicated Tmux pane that shows the REPL/Output even if the main editor layout changes.
- **Visual Breakpoints**: Use nvim-dap to set breakpoints, but let the execution reside in the "indestructible" background.
- **Remote Attach**: Ability to attach to a running debugger from a different terminal window or even a different machine.
