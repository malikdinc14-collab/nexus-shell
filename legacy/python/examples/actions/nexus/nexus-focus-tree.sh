#!/bin/bash
# @parallax-action
# @name: Focus Tree
# @id: nexus:focus-tree
# @description: Switch focus to the file tree pane
# @icon: folder-tree

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
exec "$PY" "$NEXUS_HOME/core/engine/actions/dispatch.py" pane.focus tree
