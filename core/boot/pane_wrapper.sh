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

    # Instead of launching the FZF menu (which now runs in-pane and expects TTY),
    # we just pause and wait for the user to decide what to do.
    echo ""
    echo -e "\033[1;33m  [Nexus] Process exited or crashed.\033[0m"
    echo -e "  Press \033[1;32mENTER\033[0m to restart the tool, or type '\033[1;36mshell\033[0m' to drop to zsh."
    echo ""
    read -r action
    
    if [[ "$action" == "shell" ]]; then
        /bin/zsh -i
    fi
    # Returning from this function will trigger run_tool to respawn the command
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
