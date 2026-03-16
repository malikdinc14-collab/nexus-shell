#!/bin/bash
# core/exec/nxs-switch.sh
# Respawns the current pane with a specific Nexus tool.

TOOL="$1"
PANE_ID="${PANE_ID:-$(tmux display-message -p '#{pane_id}')}"

# Source Nexus environment if not set
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"
export NEXUS_CORE="${NEXUS_CORE:-$NEXUS_HOME/core}"

case "$TOOL" in
    menu)     CMD="$NEXUS_HOME/modules/menu/bin/nexus-menu" ;;
    chat)     CMD="${NEXUS_CHAT:-opencode}" ;;
    edit)     CMD="${NEXUS_EDITOR:-nvim}" ;;
    explorer) CMD="${NEXUS_FILES:-yazi}" ;;
    view)     CMD="$NEXUS_HOME/core/view/nxs-view" ;;
    shelf)    CMD="$NEXUS_HOME/modules/menu/bin/nexus-menu --context shelf" ;;
    *)        echo "Unknown tool: $TOOL"; exit 1 ;;
esac

tmux respawn-pane -k -t "$PANE_ID" "$NEXUS_HOME/core/boot/pane_wrapper.sh $CMD"
