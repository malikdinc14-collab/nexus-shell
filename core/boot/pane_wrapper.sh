#!/bin/bash

# --- Nexus Pane Wrapper ---
# Indestructible viewports with FZF tool switching

# 1. Zero-Entropy Path Resolution
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_SCRIPTS="$SCRIPT_DIR"

# 2. Unified Logging
LOG="/tmp/nexus_station.log"
echo "[$(date)] PANE_WRAPPER PID:$$ STARTING CMD: $*" >> "$LOG"

# 3. Invariant Assertion: Environment Integrity
if [[ -z "$TMUX" && -z "$TERM_PROGRAM" && ! -t 0 ]]; then
    echo "[!] INVARIANT VIOLATION: Execution without TTY or TMUX context." >> "$LOG"
    exit 101 
fi

# 4. Process Containment: Cleanup children on exit
trap 'pkill -P $$; exit 0' SIGTERM SIGINT SIGHUP

COMMAND="$@"
SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null || echo "detached")

show_hub() {
    clear
    # Ensure we don't spin if there's no TTY
    if [[ ! -t 0 ]]; then
        echo "[!] PANE WAITING FOR ATTACHMENT..."
        while [[ ! -t 0 ]]; do sleep 2; done
    fi

    # Instead of a hardcoded FZF menu, use the centralized Nexus-Menu pipeline.
    # We pipe the output into the Router exactly like the main Parallax bar does.
    # The context 'system:modules' can be added to the python engine, or we can just run the generic 'system' context for now.
    MENU_BIN="${NEXUS_HOME:-/Users/Shared/Projects/nexus-shell}/modules/menu/bin/nexus-menu"
    ROUTER_BIN="${NEXUS_HOME:-/Users/Shared/Projects/nexus-shell}/core/exec/router.sh"
    
    # We set a temporary context so the menu opens to the system tools by default
    export PX_CTX_FILE="/tmp/nexus_pane_hub_$$"
    echo "system" > "$PX_CTX_FILE"
    
    # Run the standard menu -> router pipeline
    $MENU_BIN | $ROUTER_BIN
    
    # If the router executes something that exits immediately, give it a tiny delay to avoid a crazy spinning loop
    sleep 0.5
}

run_tool() {
    [[ -z "$COMMAND" ]] && return
    echo "[$(date)] PANE_WRAPPER PID:$$ RUNNING: $COMMAND" >> "$LOG"
    eval "$COMMAND"
}

# Main loop
if [[ -n "$COMMAND" ]]; then
    run_tool
fi

while true; do
    show_hub
    run_tool
    sleep 1
done
