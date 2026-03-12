# Idea: Global Jump-to-Definition

## Problem Statement
When debugging in a terminal pane (e.g., running tests), users often see stack traces. To navigate to the error, they have to manually open the file in the editor pane and jump to the line. This breaks flow.

## Proposed Solution
A mouse-aware or keyboard-driven "Jump" command that parses the current pane's output, identifies `file:line` patterns, and instantly commands the editor (Neovim) in another pane to navigate there.

## Key Features
- **Regex Parsing**: Intelligent detection of stack trace patterns (Python, Rust, JS, etc.).
- **Tmux Interop**: Use `tmux capture-pane` to scrape the context.
- **Nvim RPC**: Use `--server <pipe> --remote` for zero-latency navigation.
- **Global Keybind**: `Alt-j` (Jump) to trigger the scan on the current pane.
