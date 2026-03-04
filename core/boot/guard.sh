#!/bin/bash
# guard.sh - Handle safe exit and shutdown of Nexus session

ACTION="$1"
SESSION_ID=$(tmux display-message -p '#S' 2>/dev/null || echo "nexus_$(basename $(pwd))")
GUARD_PATH="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)/guard.sh"

case "$ACTION" in
    exit)
        # Kill the session directly
        tmux kill-session -t "$SESSION_ID" 2>/dev/null || true
        ;;
    force)
        echo "🛑 Shutting down Nexus Intelligence Stack..."
        # 1. Stop background agents
        pkill -f "px-bridge-agent" 2>/dev/null || true
        pkill -f "opencode" 2>/dev/null || true
        
        # 2. Kill the tmux session
        tmux kill-session -t "$SESSION_ID" 2>/dev/null || true
        echo "✅ Shutdown complete."
        ;;
esac
