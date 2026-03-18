#!/bin/bash
# core/kernel/exec/gap-spec.sh
# Multi-tab Spec Manager for GAP Missions using nxs-tab engine.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
GAP_DIR="$NEXUS_HOME/.gap"
SPECS_DIR="$NEXUS_HOME/specs" # Global fallback

TYPE="${1}" # requirements, design, tasks, status

# 1. Discover Active Mission
MISSION_ID=$(ls -td "$GAP_DIR/features"/*/ 2>/dev/null | head -1 | xargs basename)

if [[ -z "$MISSION_ID" ]]; then
    echo "[!] No active GAP mission found."
    tmux set -g @gap_mission ""
    exit 1
fi

tmux set -g @gap_mission "$MISSION_ID"
FEATURE_DIR="$GAP_DIR/features/$MISSION_ID"

# 2. Initialization Logic (Spawn the stack)
PANE_TITLE=$(tmux display-message -p '#{pane_title}')
if [[ "$PANE_TITLE" == "gap-spec" ]]; then
    # We are the master pane, populate the others
    # Tab 1 (Current) -> Requirements
    tmux select-pane -T "gap-spec:1"
    
    # Spawn others
    $NEXUS_HOME/core/kernel/exec/tabs.sh gap-spec new "$0 design"
    $NEXUS_HOME/core/kernel/exec/tabs.sh gap-spec new "$0 tasks"
    $NEXUS_HOME/core/kernel/exec/tabs.sh gap-spec new "$0 status"
    
    # Fallback to requirements for this pane
    TYPE="requirements"
fi

# 3. Render Content
case "$TYPE" in
    design) FILE="$FEATURE_DIR/design.md" ;;
    tasks)  FILE="$FEATURE_DIR/tasks.md" ;;
    status) FILE="$FEATURE_DIR/status.yaml" ;;
    *)      FILE="$FEATURE_DIR/requirements.md" ;;
esac

if [[ -f "$FILE" ]]; then
    # Use bat for high-fidelity rendering
    # We use --paging=always to keep the pane active and scrollable
    bat --paging=always "$FILE"
else
    echo "[!] File not found: $FILE"
    # Keep the pane alive for recovery
    /bin/zsh
fi
