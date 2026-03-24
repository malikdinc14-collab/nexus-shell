#!/bin/bash
# core/kernel/exec/focus.sh — Focus a pane by its @nexus_stack_id
# Uses tmux user options for reliable pane targeting.
# Accepts multiple IDs — tries each in order (first match wins).
# Usage: focus.sh <stack_id> [stack_id...]

if [[ $# -eq 0 ]]; then
    echo "Usage: focus.sh <stack_id> [stack_id...]" >&2
    exit 1
fi

for STACK_ID in "$@"; do
    # Search current window first
    PANE=$(tmux list-panes -F '#{pane_id}' \
        -f "#{==:#{@nexus_stack_id},$STACK_ID}" 2>/dev/null | head -1)

    if [[ -n "$PANE" ]]; then
        tmux select-pane -t "$PANE"
        exit 0
    fi

    # Fallback: search all windows in the session
    PANE=$(tmux list-panes -s -F '#{pane_id}' \
        -f "#{==:#{@nexus_stack_id},$STACK_ID}" 2>/dev/null | head -1)

    if [[ -n "$PANE" ]]; then
        tmux select-pane -t "$PANE"
        exit 0
    fi
done
