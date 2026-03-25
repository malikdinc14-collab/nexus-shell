#!/usr/bin/env bash
# pane-split.sh — Split pane (Alt+v / Alt+s)
# Layer 1 entry point. Delegates to action layer.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3

DIRECTION="${1:-v}"
exec "$PY" "$NEXUS_HOME/core/engine/actions/dispatch.py" pane.split "$DIRECTION"
