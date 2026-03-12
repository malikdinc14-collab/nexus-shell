# Requirements: Status HUD

## Functional Requirements
1.  **Rendering**: A 1-line strip at the bottom of the terminal.
2.  **Telemetry Data**:
    - **Agent State** (Idle, Thinking, Doing, Blocked).
    - **Current Workspace Name**.
    - **Model Locality** (M1, M4, Cloud).
3.  **Visibility**: Must remain visible regardless of active Tmux window/pane changes.
4.  **Auto-Update**: Updates automatically when the underlying telemetry file changes.

## Technical Requirements
- **Tmux Integration**: Use a dedicated Tmux window (e.g., `[HUD]`) or a custom status bar override.
- **TUI Framework**: Bash with ANSI codes or a small Python TUI script for high-fidelity rendering.
- **IPC**: Read from `/tmp/nexus_telemetry.json`.

## Non-Functional Requirements
- **Zero Impact**: Must consume <1% CPU when idle.
- **Aesthetics**: Must use `nxs-theme` tokens for premium visual consistency.
