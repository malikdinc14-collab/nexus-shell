#!/bin/bash
# core/engine/search/live_grep.sh — Project-Wide Grep Search (tmux popup)
# Opens a floating fzf window with ripgrep, jumps to file:line in nvim.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null)
PROJECT_NAME=${SESSION_NAME#nexus_}
NVIM_PIPE="$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe"

INITIAL_QUERY="${1:-}"

# Resolve search paths (colon-separated NEXUS_ROOTS or current directory)
IFS=':' read -ra SEARCH_PATHS <<< "${NEXUS_ROOTS:-.}"

# Ripgrep + fzf with live reload
SELECTION=$(FZF_DEFAULT_COMMAND="rg --column --line-number --no-heading --color=always --smart-case '${INITIAL_QUERY:-.}' ${SEARCH_PATHS[@]}" \
    fzf --ansi --layout=reverse --border=rounded \
        --prompt="🔎 Grep > " \
        --header="Live Grep (type to search)" \
        --disabled --query "$INITIAL_QUERY" \
        --bind "change:reload:rg --column --line-number --no-heading --color=always --smart-case {q} ${SEARCH_PATHS[@]} || true" \
        --preview 'bat --color=always --style=numbers --highlight-line {2} {1} 2>/dev/null' \
        --preview-window='right:60%:+{2}-10' \
        --delimiter ':')

if [[ -n "$SELECTION" ]]; then
    FILE=$(echo "$SELECTION" | cut -d: -f1)
    LINE=$(echo "$SELECTION" | cut -d: -f2)

    if [[ -S "$NVIM_PIPE" ]]; then
        nvim --server "$NVIM_PIPE" --remote "$(pwd)/$FILE" 2>/dev/null
        # Jump to line
        nvim --server "$NVIM_PIPE" --remote-send ":${LINE}<CR>zz" 2>/dev/null
    else
        tmux send-keys -t editor "nvim '+$LINE' '$FILE'" Enter
    fi
    tmux select-pane -t editor
fi
