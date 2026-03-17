#!/bin/bash
# core/engine/ai/send_context.sh — Send current editor context to the AI chat pane
# Reads the current nvim buffer (or selection) and pipes it to the chat tool.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null)
PROJECT_NAME=${SESSION_NAME#nexus_}
NVIM_PIPE="$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe"

if [[ ! -S "$NVIM_PIPE" ]]; then
    tmux display-message "No nvim server found. Open a file first."
    exit 1
fi

# Get current file path and buffer contents
CURRENT_FILE=$(nvim --server "$NVIM_PIPE" --remote-expr "expand('%:p')" 2>/dev/null)
BUFFER=$(nvim --server "$NVIM_PIPE" --remote-expr "join(getline(1, '$'), \"\\n\")" 2>/dev/null | head -200)

if [[ -z "$BUFFER" ]]; then
    tmux display-message "Buffer is empty."
    exit 1
fi

# Write to a temp file for the AI to read
CONTEXT_FILE="/tmp/nexus_ai_context.txt"
echo "=== File: $CURRENT_FILE ===" > "$CONTEXT_FILE"
echo "$BUFFER" >> "$CONTEXT_FILE"

# Send to the chat pane
tmux send-keys -t chat "Please review this file: $CURRENT_FILE" Enter
sleep 0.2
tmux send-keys -t chat "$(cat "$CONTEXT_FILE")" Enter

tmux display-message "Context sent to AI ($(wc -l < "$CONTEXT_FILE") lines)"
