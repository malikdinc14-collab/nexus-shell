# Research: Architectural Stress Tests

This document contains final theoretical validations before implementation.

## 1. The Focus Catch-22 (Non-Tmux)
**Problem**: In tmux, `Alt+N` triggers a shell script. In a standalone terminal window (e.g., iTerm2), the terminal owns the keybindings.
**Resolution**: 
-   **Terminal-Side Integration**: Use **OSC codes** (`OSC 7` or similar) to report the current directory and focus state of the shell to the Nexus Daemon.
-   **Global Shortcuts**: Users on standalone windows will likely use an **os-level shortcut** (e.g., via hammerspoon or raycast) to trigger the `stack` client with the correct `window_id`.

## 2. Geometric Resolution Invariance
**Problem**: If you save your layout on a 4K monitor and restore it on a 1080p laptop screen, the absolute coordinates will fail.
**Resolution**: 
-   **Proportional Stacking**: Instead of `x=500px, y=300px`, use **Percentages** (`x=0.25, y=0.33, w=0.5, h=0.5`).
-   **Nearest-Neighbor Mapping**: On restoration, the system identifies the pane whose "Center Gravity" is closest to the saved Proportional Anchor.

## 3. The "Ghost" Pane Problem
**Problem**: What if a stack exists in memory but has no physical container anymore (e.g. you closed the window)?
**Resolution**: 
-   **The Reservoir**: All stacks without a window are moved to the **Reservoir** (the background). They stay alive and can be called back to any window at any time.

## 4. Multi-Multiplexer Conflict
**Problem**: What if a user runs tmux INSIDE a standalone window?
**Resolution**: 
-   **Hierarchy of Adapters**: The IPC bridge should detect the "Inner-most" identity. If tmux is present, the `TmuxAdapter` takes precedence. If not, the `WindowAdapter` handles it.
