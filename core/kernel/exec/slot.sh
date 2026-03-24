#!/bin/bash
# core/kernel/exec/slot.sh — Project slot switcher
# Thin entry point, delegates to action layer.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

SLOT="${1}"
if [[ -z "$SLOT" ]]; then
    echo "Usage: slot.sh <1-9>"
    exit 1
fi

exec "$PY" "$DISPATCH" pane.select-window ":${SLOT}"
