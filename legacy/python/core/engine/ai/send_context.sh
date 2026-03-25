#!/bin/bash
# core/engine/ai/send_context.sh — Send current editor context to the AI chat pane
# Layer 1 entry point. Uses action layer for editor and pane operations.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

# Get current file path via editor adapter
CURRENT_FILE=$("$PY" "$DISPATCH" editor.current-file 2>/dev/null)
if [[ -z "$CURRENT_FILE" ]]; then
    echo "[INVARIANT] No editor session or empty buffer." >&2
    exit 1
fi

# Get buffer content via editor adapter
BUFFER=$("$PY" "$DISPATCH" editor.buffer 200 2>/dev/null)
if [[ -z "$BUFFER" ]]; then
    echo "[INVARIANT] Buffer is empty." >&2
    exit 1
fi

# Write to a temp file for the AI to read
CONTEXT_FILE="/tmp/nexus_ai_context.txt"
echo "=== File: $CURRENT_FILE ===" > "$CONTEXT_FILE"
echo "$BUFFER" >> "$CONTEXT_FILE"

# Send to the chat pane via action layer
"$PY" "$DISPATCH" pane.send-command chat "Please review this file: $CURRENT_FILE"
sleep 0.2
"$PY" "$DISPATCH" pane.send-command chat "$(cat "$CONTEXT_FILE")"
