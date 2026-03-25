#!/bin/bash
# --- Nexus Tree/Git Swap ---
# Toggles the tree pane between File Navigator (Yazi) and Git UI (LazyGit)
# Layer 1 entry point. Uses action layer for pane operations.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"

# Tool defaults
NEXUS_FILES="${NEXUS_FILES:-yazi}"
NEXUS_GIT="${NEXUS_GIT:-lazygit}"

MODE_FILE="$NEXUS_STATE/tree_mode"

# Get current mode (default: files)
CURRENT_MODE="files"
[[ -f "$MODE_FILE" ]] && CURRENT_MODE="$(cat "$MODE_FILE")"

# Find tree pane handle via metadata
TREE_PANE=$("$PY" "$DISPATCH" pane.id 2>/dev/null)
# TODO: resolve tree pane by role once pane.focus_by_role works reliably

case "$CURRENT_MODE" in
    "files")
        echo "git" > "$MODE_FILE"
        "$PY" "$DISPATCH" pane.respawn "${TREE_PANE:-}" "$NEXUS_GIT"
        ;;
    "git")
        echo "files" > "$MODE_FILE"
        "$PY" "$DISPATCH" pane.respawn "${TREE_PANE:-}" "$NEXUS_FILES"
        ;;
esac
