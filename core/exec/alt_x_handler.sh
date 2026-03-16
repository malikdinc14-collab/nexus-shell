#!/bin/bash
# alt_x_handler.sh - Intelligent Toggle for Alt-X
# Cycle: Tool -> Menu -> Terminal -> Kill Pane

# Ensure NEXUS_HOME is set
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"

PANE_ID="$1"
PANE_PID="$2"

# 1. Find the leaf process (deepest child)
find_leaf() {
    local parent="$1"
    # Get the youngest/most recent child (head -n 1 of pgrep sorts by PID by default, but we should just take the first)
    local child
    child=$(pgrep -P "$parent" | head -n 1)
    if [[ -n "$child" ]]; then
        find_leaf "$child"
    else
        echo "$parent"
    fi
}

LEAF_PID=$(find_leaf "$PANE_PID")

if [[ "$LEAF_PID" == "$PANE_PID" ]]; then
    CMD=""
else
    # Get the command string of the leaf process
    CMD=$(ps -p "$LEAF_PID" -o command= | xargs)
fi

# 2. Determine State and Route
LOG_FILE="/tmp/nexus_alt_x.log"
echo "[$(date +%T)] LEAF_PID: $LEAF_PID | CMD: $CMD" >> "$LOG_FILE"

# List of commands that count as "Active Tool"
# This list can be expanded or we can use a negative match for shells
IS_SHELL=false
if [[ "$CMD" == *"/bin/zsh"* || "$CMD" == *"zsh"* || "$CMD" == *"/bin/bash"* || -z "$CMD" ]]; then
    IS_SHELL=true
fi

IS_MENU=false
if [[ "$CMD" == *"nexus-menu"* || "$CMD" == *"nxm.py"* || "$CMD" == *"fzf"* || "$CMD" == *"px-engine"* ]]; then
    IS_MENU=true
fi

if [[ "$IS_MENU" == "true" ]]; then
    # STATE: Menu -> Terminal
    echo "[$(date +%T)] Menu detected -> Switching to Terminal" >> "$LOG_FILE"
    tmux respawn-pane -k -t "$PANE_ID" "$NEXUS_HOME/core/boot/pane_wrapper.sh /bin/zsh -i"
    
elif [[ "$IS_SHELL" == "true" ]]; then
    # STATE: Terminal (Idle) -> Menu
    echo "[$(date +%T)] Terminal detected -> Switching to Menu" >> "$LOG_FILE"
    MENU_BIN="$NEXUS_HOME/modules/menu/bin/nexus-menu"
    tmux respawn-pane -k -t "$PANE_ID" "$NEXUS_HOME/core/boot/pane_wrapper.sh $MENU_BIN --context modules"

else
    # STATE: Active Tool -> Menu
    echo "[$(date +%T)] Tool detected ($CMD) -> Switching to Menu" >> "$LOG_FILE"
    MENU_BIN="$NEXUS_HOME/modules/menu/bin/nexus-menu"
    tmux respawn-pane -k -t "$PANE_ID" -e "SESSION_ID=$SESSION_ID" -e "PROJECT_ROOT=$PROJECT_ROOT" -e "NEXUS_HOME=$NEXUS_HOME" "$NEXUS_HOME/core/boot/pane_wrapper.sh $MENU_BIN --context system"
fi
