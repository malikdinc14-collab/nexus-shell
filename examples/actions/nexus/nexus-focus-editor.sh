#!/bin/bash
# @parallax-action
# @name: Focus Editor
# @id: nexus:focus-editor
# @description: Switch focus to the editor pane
# @icon: code

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
exec "$PY" "$NEXUS_HOME/core/engine/actions/dispatch.py" pane.focus editor
