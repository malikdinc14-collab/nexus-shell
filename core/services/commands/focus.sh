#!/usr/bin/env bash
# core/services/commands/focus.sh
# Toggles the zoom (focus) state of the current pane.
# Uses action layer for all multiplexer operations.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

# Toggle zoom via action layer
"$PY" "$DISPATCH" pane.zoom
