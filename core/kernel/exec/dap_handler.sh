#!/usr/bin/env bash
# core/kernel/exec/dap_handler.sh
# Manages the Headless DAP lifecycle (Start/Stop/Attach)

ACTION="${1:-status}"
COMMAND="${2:-}"

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
SESSION_ID=$(tmux display-message -p '#S' 2>/dev/null)
DEBUG_PANE_ID="9"

case "$ACTION" in
    start)
        local target_file="$COMMAND"
        if [[ -z "$target_file" ]]; then
            echo "[!] Error: No target file specified for :debug start"
            exit 1
        fi

        tmux display-message "Starting Headless DAP for $(basename "$target_file")..."
        
        # 1. Provision the Debug Console window if it doesn't exist
        if ! tmux has-session -t "$SESSION_ID:DAP" 2>/dev/null; then
            tmux new-window -d -t "$SESSION_ID:$DEBUG_PANE_ID" -n "DAP" -c "$(pwd)"
        fi
        
        # 2. Launch the language-specific server in the DAP pane
        tmux send-keys -t "$SESSION_ID:DAP" "${NEXUS_HOME}/core/kernel/exec/dap_languages.sh '$target_file'" Enter
        ;;

    stop)
        tmux display-message "Terminating Debug Session..."
        tmux kill-window -t "$SESSION_ID:DAP" 2>/dev/null
        ;;

    attach)
        tmux select-window -t "$SESSION_ID:DAP"
        ;;

    *)
        echo "Usage: :debug {start|stop|attach}"
        ;;
esac
