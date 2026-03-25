#!/bin/bash
# core/engine/ai/pipe_error.sh — Pipe terminal errors to the AI chat pane
# Layer 1 entry point. Uses action layer for pane operations.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

LINES="${1:-30}"

# Capture terminal pane output via action layer
ERROR_CONTEXT=$("$PY" "$DISPATCH" pane.capture terminal "$LINES" 2>/dev/null | tail -"$LINES")

if [[ -z "$ERROR_CONTEXT" ]]; then
    echo "[INVARIANT] No terminal output to capture." >&2
    exit 1
fi

# Send to chat pane via action layer
"$PY" "$DISPATCH" pane.send-command chat "I got this error. Can you help debug it?"
sleep 0.2
"$PY" "$DISPATCH" pane.send-command chat "$ERROR_CONTEXT"
