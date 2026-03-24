#!/bin/bash
# core/engine/search/quick_find.sh — Project-Wide File Search (tmux popup)
# Opens fzf for file selection, sends to editor via action layer.
# fzf stays in shell. Editor/pane calls go through adapter layer.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

# Resolve search paths
IFS=':' read -ra SEARCH_PATHS <<< "${NEXUS_ROOTS:-.}"

# Use fd if available, otherwise find
if command -v fd &>/dev/null; then
    FIND_CMD="fd --type f --hidden --exclude .git . ${SEARCH_PATHS[@]}"
else
    FIND_CMD="find ${SEARCH_PATHS[@]} -type f -not -path '*/.git/*'"
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
    # Open file via action layer (handles editor RPC + pane focus)
    "$PY" "$DISPATCH" editor.open "$(pwd)/$FILE"
fi
