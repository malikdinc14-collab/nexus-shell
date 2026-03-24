#!/usr/bin/env bash
# core/kernel/nav/jump.sh
# Scrapes the current pane for file:line patterns and navigates the editor.
# fzf stays in shell. File opening goes through action layer.

# Dependencies: fzf

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

# Capture current pane output via action layer
CONTENT=$("$PY" "$DISPATCH" pane.capture "" 200 2>/dev/null)

# Extract patterns like "/path/to/file:123" or "./file.py:123"
# Filter to ensure the file actually exists
SELECTABLE=$(echo "$CONTENT" | grep -oE "[a-zA-Z0-9._/-]+\.[a-zA-Z0-9]+:[0-9]+" | sort -u | while read -r line; do
    file="${line%%:*}"
    if [[ -f "$file" ]]; then echo "$line"; fi
done)

if [[ -z "$SELECTABLE" ]]; then
    echo "[INVARIANT] No jump targets found in pane." >&2
    exit 0
fi

# Pick target via fzf-tmux (popup) — fzf is a shell tool, stays here
TARGET=$(echo "$SELECTABLE" | fzf-tmux -p --reverse --prompt="Jump to > ")

if [[ -n "$TARGET" ]]; then
    FILE="${TARGET%%:*}"
    LINE="${TARGET#*:}"

    # Open file at line via action layer (handles editor RPC + pane focus)
    "$PY" "$DISPATCH" editor.open "$(realpath "$FILE")" "$LINE"
fi
