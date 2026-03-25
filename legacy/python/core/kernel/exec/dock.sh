#!/bin/bash
# core/kernel/exec/dock.sh — Thin entry point for dock toggle
# All multiplexer logic lives in core/engine/actions/dock.py

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3

exec "$PY" "$NEXUS_HOME/core/engine/actions/dock.py" "${1:-toggle}"
