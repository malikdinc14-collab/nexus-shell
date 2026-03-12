# Requirements: Global Jump-to-Definition

## Functional Requirements
1.  **Pattern Recognition**: Detect `file:line` syntax (absolute and relative).
2.  **Interactive Selection**: Present multiple targets in a fuzzy-finder if multiple exist in the pane.
3.  **Cross-Pane Navigation**: Send the command to the "editor" pane, even if triggered from "terminal" or "logs".
4.  **Editor Support**: Zero-latency jump using Neovim RPC.

## Technical Requirements
- **Dependencies**: `fzf-tmux`, `rg`, `realpath`.
- **IPC**: Read the active Nvim pipe from `/tmp/nexus_$(whoami)/pipes/`.

## Non-Functional Requirements
- **Speed**: Target detection and TUI popup should appear in <100ms.
- **Accuracy**: Filter results to only show files that actually exist on disk.
