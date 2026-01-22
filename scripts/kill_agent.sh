#!/bin/bash
# kill_agent.sh - Terminate active agent processes

set -e

echo "🛑 Terminating active agent processes..."
# Kill px-bridge-agent and any active opencode/aider processes
pkill -f "px-bridge-agent" || true
pkill -f "opencode" || true
pkill -f "aider" || true

tmux display-message "✅ Active agents terminated."
rm -f /tmp/px-agent-trace.log
touch /tmp/px-agent-trace.log
