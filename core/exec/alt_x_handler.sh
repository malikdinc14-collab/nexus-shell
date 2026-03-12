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
if [[ "$CMD" == *"nexus-menu"* || "$CMD" == *"fzf"* || "$CMD" == *"px-engine"* ]]; then
    # STATE 2: Menu is running -> Drop to an empty Terminal
    # We use pane_wrapper so it's indestructible
    tmux respawn-pane -k -t "$PANE_ID" "$NEXUS_HOME/core/boot/pane_wrapper.sh /bin/zsh -i"
    
elif [[ "$CMD" == *"/bin/zsh"* || "$CMD" == *"zsh"* || "$CMD" == *"/bin/bash"* || -z "$CMD" ]]; then
    # STATE 3: Just a shell is running -> Kill the pane
    PANE_COUNT=$(tmux list-panes | wc -l)
    if [[ "$PANE_COUNT" -gt 1 ]]; then
        tmux kill-pane -t "$PANE_ID"
    else
        tmux display-message "Cannot close the last pane."
    fi
    
else
    # STATE 1: A Tool or Script is running -> Open the Universal Stack Manager
    # This provides the polymorphic stack selection (Tools, Models, etc.)
    STACK_MGR="$NEXUS_CORE/exec/stack_manager.sh"
    if [[ -x "$STACK_MGR" ]]; then
        # Run it directly in the pane
        tmux respawn-pane -k -t "$PANE_ID" "$NEXUS_CORE/boot/pane_wrapper.sh $STACK_MGR $ROLE"
    else
        # Fallback to menu if manager missing
        tmux respawn-pane -k -t "$PANE_ID" "$NEXUS_CORE/boot/pane_wrapper.sh $NEXUS_HOME/modules/menu/bin/nexus-menu"
    fi
fi
