#!/bin/bash
# core/engine/search/live_grep.sh — Project-Wide Grep Search (tmux popup)
# Opens fzf with ripgrep, sends selection to editor via action layer.
# fzf is inherently terminal — it stays in shell. Only the editor/pane
# calls go through the adapter layer.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

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
    COL=$(echo "$SELECTION" | cut -d: -f3)

    # Open file at line:col via action layer (handles editor RPC + pane focus)
    "$PY" "$DISPATCH" editor.open "$(pwd)/$FILE" "$LINE" "${COL:-1}"
fi
