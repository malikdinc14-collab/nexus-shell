#!/usr/bin/env bash
# core/exec/dap_handler.sh
# Manages the Headless DAP lifecycle (Start/Stop/Attach)

ACTION="${1:-status}"
COMMAND="${2:-}"

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
SESSION_ID=$(tmux display-message -p '#S' 2>/dev/null)
DEBUG_PANE_ID="9"

case "$ACTION" in
    start)
        tmux display-message "Starting Headless DAP..."
        # 1. Provision the Debug Console window if it doesn't exist
        if ! tmux has-session -t "$SESSION_ID:DAP" 2>/dev/null; then
            tmux new-window -d -t "$SESSION_ID:$DEBUG_PANE_ID" -n "DAP" -c "$(pwd)"
        fi
        
        # 2. Logic to detect language and start appropriate DAP server
        # (This will be expanded with language-specific loaders)
        tmux send-keys -t "$SESSION_ID:DAP" "echo '[*] Waiting for Debug Adapter...'" Enter
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
