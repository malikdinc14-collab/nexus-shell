#!/bin/bash
# guard.sh - Handle safe exit and shutdown of Nexus session

ACTION="$1"
SESSION_ID=$(tmux display-message -p '#S' 2>/dev/null || echo "nexus_$(basename $(pwd))")
PROJECT_ROOT=$(pwd)

case "$ACTION" in
    exit)
        # Ask for confirmation before killing the session
        # Use a popup if in tmux
        if [[ -n "$TMUX" ]]; then
            tmux confirm-before -p "🛑 Kill session and stop all AI models? (y/n)" "run-shell '$0 force'"
        else
            read -p "🛑 Kill session and stop all AI models? (y/N): " confirm
            if [[ $confirm == [yY] ]]; then
                "$0" force
            fi
        fi
        ;;
    force)
        echo "🛑 Shutting down Nexus Intelligence Stack..."
        # 1. Stop background agents
        pkill -f "px-bridge-agent" || true
        pkill -f "opencode" || true
        
        # 2. Unload brains
        [[ -x "$NEXUS_BOOT/unload_brains.sh" ]] && "$NEXUS_BOOT/unload_brains.sh"
        
        # 3. Stop resource guard
        [[ -x "$NEXUS_HOME/modules/parallax/content/actions/intel/resource-guard" ]] && \
            export ACTION=stop && "$NEXUS_HOME/modules/parallax/content/actions/intel/resource-guard"
            
        # 4. Kill the tmux session
        tmux kill-session -t "$SESSION_ID" 2>/dev/null || true
        echo "✅ Shutdown complete."
        ;;
esac
