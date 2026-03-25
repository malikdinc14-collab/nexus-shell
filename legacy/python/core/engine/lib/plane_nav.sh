#!/usr/bin/env zsh
# lib/plane_nav.sh
# Coordinate-based 2D navigation for Nexus-Shell 5-pane layout
# Layer 1 entry point. Uses action layer for pane focus.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

DIRECTION=$1
CUR_PANE_INDEX=$("$PY" "$DISPATCH" pane.metadata "$("$PY" "$DISPATCH" pane.id)" pane_index 2>/dev/null)

# Use exported indices from launcher.sh, fallback to standard layout
TREE=${PX_NEXUS_TREE_PANE:-0}
PARALLAX=${PX_NEXUS_PARALLAX_PANE:-1}
EDITOR=${PX_NEXUS_EDITOR_PANE:-2}
TERMINAL=${PX_NEXUS_TERMINAL_PANE:-3}
CHAT=${PX_NEXUS_CHAT_PANE:-4}

# Resolve target pane index based on direction and current position
TARGET=""
case "$DIRECTION" in
    "up")
        [[ "$CUR_PANE_INDEX" == "$TERMINAL" ]] && TARGET="$EDITOR"
        [[ "$CUR_PANE_INDEX" == "$EDITOR" ]] && TARGET="$PARALLAX"
        ;;
    "down")
        [[ "$CUR_PANE_INDEX" == "$PARALLAX" ]] && TARGET="$EDITOR"
        [[ "$CUR_PANE_INDEX" == "$EDITOR" ]] && TARGET="$TERMINAL"
        ;;
    "left")
        [[ "$CUR_PANE_INDEX" == "$CHAT" ]] && TARGET="$EDITOR"
        [[ "$CUR_PANE_INDEX" == "$PARALLAX" || "$CUR_PANE_INDEX" == "$EDITOR" || "$CUR_PANE_INDEX" == "$TERMINAL" ]] && TARGET="$TREE"
        ;;
    "right")
        [[ "$CUR_PANE_INDEX" == "$TREE" ]] && TARGET="$EDITOR"
        [[ "$CUR_PANE_INDEX" == "$PARALLAX" || "$CUR_PANE_INDEX" == "$EDITOR" || "$CUR_PANE_INDEX" == "$TERMINAL" ]] && TARGET="$CHAT"
        ;;
esac

[[ -n "$TARGET" ]] && "$PY" "$DISPATCH" pane.focus "%$TARGET"
