#!/bin/bash
# core/kernel/exec/tabs.sh — Thin entry point for tab operations
# All multiplexer logic lives in core/engine/actions/tabs.py

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3

exec "$PY" "$NEXUS_HOME/core/engine/actions/tabs.py" "${1:-}" "${2:-next}" "${3:-}"
