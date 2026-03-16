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

    # THE PORTAL (Alt-X) Logic
    # 1. Any Tool -> Menu
    # 2. Menu -> Terminal
    # 3. Terminal -> Menu
    
    echo "[$(date +%T)] Triggering Portal Switch" >> "$LOG_FILE"
    STACK_BIN="$NEXUS_HOME/core/stack/nxs-stack"
    MENU_BIN="$NEXUS_HOME/modules/menu/bin/nexus-menu"
    FZF_MENU_BIN="$NEXUS_HOME/modules/menu/bin/nxs-menu-fzf"

    # Helper: Find Menu Index in local stack
    FIND_MENU_IDX() {
        "$STACK_BIN" list local | jq '.tabs | to_entries | .[] | select(.value.name == "Menu") | .key' 2>/dev/null
    }

    if [[ "$IS_MENU" == "true" ]]; then
        # STATE: Menu -> Terminal (Foundation)
        echo "[$(date +%T)] Menu detected -> Switching to nexus-terminal (Index 0)" >> "$LOG_FILE"
        "$STACK_BIN" switch local 0
    else
        # STATE: Tool/Terminal -> Menu (Portal)
        MENU_IDX=$(FIND_MENU_IDX)
        
        if [[ -n "$MENU_IDX" ]]; then
             echo "[$(date +%T)] Existing Menu found at index $MENU_IDX -> Switching" >> "$LOG_FILE"
             # Hardening: Check if the menu pane actually exists before switching
             if "$STACK_BIN" switch local "$MENU_IDX"; then
                exit 0
             fi
             echo "[$(date +%T)] Menu switch failed (stale ID). Forcing fresh launch." >> "$LOG_FILE"
        fi

        # TIERED LAUNCHER
        # Try Tier 1 (Premium) unless Stable Mode is forced
        if [[ "$NXS_STABLE_MODE" != "true" ]]; then
            echo "[$(date +%T)] Attempting Tier 1 (Textual) Launch" >> "$LOG_FILE"
            if "$STACK_BIN" push local "$MENU_BIN --context system" "Menu"; then
                exit 0
            fi
            echo "[$(date +%T)] Tier 1 Failed. Falling back to Tier 0." >> "$LOG_FILE"
        fi

        # Fallback to Tier 0 (Bulletproof)
        echo "[$(date +%T)] Launching Tier 0 (FZF) Fallback" >> "$LOG_FILE"
        "$STACK_BIN" push local "$FZF_MENU_BIN --context system" "Menu"
    fi
