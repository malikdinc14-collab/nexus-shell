#!/bin/bash
# @parallax-action
# @name: Focus Terminal
# @id: nexus:focus-terminal
# @description: Switch focus to the terminal pane
# @icon: terminal

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
exec "$PY" "$NEXUS_HOME/core/engine/actions/dispatch.py" pane.focus terminal
