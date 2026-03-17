#!/usr/bin/env bash
# core/kernel/nav/jump.sh
# Scrapes the current Tmux pane for file:line patterns and navigates the editor.

# Dependencies: rg, fzf, nvim (with RPC)

# Get current pane content
CONTENT=$(tmux capture-pane -p)

# Extract patterns like "/path/to/file:123" or "./file.py:123"
# Filter to ensure the file actually exists
SELECTABLE=$(echo "$CONTENT" | grep -oE "[a-zA-Z0-9._/-]+\.[a-zA-Z0-9]+:[0-9]+" | sort -u | while read -r line; do
    file="${line%%:*}"
    if [[ -f "$file" ]]; then echo "$line"; fi
done)

if [[ -z "$SELECTABLE" ]]; then
    tmux display-message "No jump targets found in pane."
    exit 0
fi

# Pick target via fzf-tmux (popup)
TARGET=$(echo "$SELECTABLE" | fzf-tmux -p --reverse --prompt="🚀 Jump to > ")

if [[ -n "$TARGET" ]]; then
    FILE="${TARGET%%:*}"
    LINE="${TARGET#*:}"
    
    # Find editor pipe
    SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null)
    PROJECT_NAME=${SESSION_NAME#nexus_}
    NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe"
    
    if [[ -S "$NVIM_PIPE" ]]; then
        # Navigate
        nvim --server "$NVIM_PIPE" --remote "$(realpath "$FILE")"
        nvim --server "$NVIM_PIPE" --remote-send ":$LINE<CR>zz"
        tmux select-pane -t editor
    else
        tmux display-message "Editor not found. Using current pane."
        nvim "+$LINE" "$FILE"
    fi
fi
