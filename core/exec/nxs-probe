#!/bin/bash
# core/exec/nxs-probe
# The Observability "Listener" for Nexus Shell

LOG_DIR="/tmp/nexus_stack_logs"
mkdir -p "$LOG_DIR"

STACK_STATE="/tmp/nexus_$(whoami)/stacks.json"

clear
echo -e "\033[1;34m[ Nexus Shell: Deep Probe ]\033[0m"
echo "------------------------------------------------"
echo "Listening to portal dispatch & stack state..."
echo ""

# Function to dump state
dump_state() {
    echo -e "\033[1;32m[ Stack State ]\033[0m"
    if [[ -f "$STACK_STATE" ]]; then
        jq '.' "$STACK_STATE" 2>/dev/null || echo "{}"
    else
        echo "State file not found at $STACK_STATE"
    fi
    echo ""
}

# Initial dump
dump_state

# Tail logs and refresh state on changes
# Monitor: alt_x.log, menu.log, stack.log
LOGS=(
    "/tmp/nexus_alt_x.log"
    "/tmp/nexus_menu.log"
    "/tmp/nexus_$(whoami)/stack.log"
)

# Open a separate pane for the log tail if in tmux, otherwise just tail here
if [[ -n "$TMUX" ]]; then
    echo "Running in TMUX mode. Spawning live tail..."
    # We use tail -f across all logs. 
    # Use fswatch or simple loop for state refresh
    while true; do
        clear
        echo -e "\033[1;34m[ Nexus Shell: Deep Probe ]\033[0m"
        echo "------------------------------------------------"
        dump_state
        echo -e "\033[1;33m[ Recent Logs ]\033[0m"
        for log in "${LOGS[@]}"; do
            if [[ -f "$log" ]]; then
                echo -e "\033[1;36m--- $(basename "$log") ---\033[0m"
                tail -n 10 "$log"
            fi
        done
        sleep 2
    done
else
    echo "Tail logs manually from /tmp/nexus_*.log"
    dump_state
fi
