#!/usr/bin/env bash
# core/services/commands/hud.sh — HUD toggle
# Thin entry point, delegates to action layer.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

case "$1" in
    toggle)
        "$PY" "$DISPATCH" pane.select-window "HUD" 2>/dev/null || \
        echo "[INVARIANT] HUD window not found." >&2
        ;;
    *) echo "Usage: hud.sh toggle" ;;
esac
