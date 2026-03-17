#!/bin/bash
# core/engine/ai/pipe_error.sh — Pipe terminal errors to the AI chat pane
# Captures the last N lines from the terminal pane and sends them to the AI.

LINES="${1:-30}"

# Capture terminal pane output
ERROR_CONTEXT=$(tmux capture-pane -t terminal -p 2>/dev/null | tail -"$LINES")

if [[ -z "$ERROR_CONTEXT" ]]; then
    tmux display-message "No terminal output to send."
    exit 1
fi

# Write to temp file
ERROR_FILE="/tmp/nexus_ai_error.txt"
echo "=== Terminal Output (last $LINES lines) ===" > "$ERROR_FILE"
echo "$ERROR_CONTEXT" >> "$ERROR_FILE"

# Send to chat pane
tmux send-keys -t chat "I got this error. Can you help debug it?" Enter
sleep 0.2
tmux send-keys -t chat "$ERROR_CONTEXT" Enter

tmux display-message "Error context sent to AI ($LINES lines)"
