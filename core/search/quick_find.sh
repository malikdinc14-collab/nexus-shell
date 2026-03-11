#!/bin/bash
# core/search/quick_find.sh — Project-Wide File Search (tmux popup)
# Opens a floating fzf window, sends the selected file to nvim in the editor pane.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null)
PROJECT_NAME=${SESSION_NAME#nexus_}
NVIM_PIPE="$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe"

# Use fd if available, otherwise find
if command -v fd &>/dev/null; then
    FIND_CMD="fd --type f --hidden --exclude .git"
else
    FIND_CMD="find . -type f -not -path '*/.git/*'"
fi

# Run fzf with preview
FILE=$($FIND_CMD | fzf \
    --ansi --layout=reverse --border=rounded \
    --prompt="🔍 Find > " \
    --header="Project Search" \
    --preview 'bat --color=always --style=numbers --line-range=:200 {} 2>/dev/null || cat {}' \
    --preview-window=right:60%:wrap \
    --bind 'ctrl-/:toggle-preview')

if [[ -n "$FILE" ]]; then
    # Open in nvim via RPC if pipe exists, otherwise send-keys
    if [[ -S "$NVIM_PIPE" ]]; then
        nvim --server "$NVIM_PIPE" --remote "$(pwd)/$FILE" 2>/dev/null
    else
        tmux send-keys -t editor "nvim '$FILE'" Enter
    fi
    # Focus the editor pane
    tmux select-pane -t editor
fi
