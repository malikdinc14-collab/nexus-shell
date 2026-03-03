#!/bin/bash
# px-bridge-agent.sh - The "Ghost Operator" Orchestrator

set -e

QUERY="$1"
TRACE_FILE="/tmp/px-agent-trace.log"
[[ ! -f "$TRACE_FILE" ]] && touch "$TRACE_FILE"

# Send "Thinking" message to Parallax Header if possible
# (Using tmux display-message for now)
tmux display-message "🧠 Agent is processing: $QUERY"

# Run the Python bridge logic
export PYTHONPATH="$(cd "$(dirname "$0")/../modules/parallax" && pwd):$PYTHONPATH"
python3 "$(dirname "$0")/px-bridge-agent.py" "$QUERY" >> "$TRACE_FILE" 2>&1
