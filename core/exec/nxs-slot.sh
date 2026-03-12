#!/bin/bash
# core/exec/nxs-slot.sh
# Manages project "slots" (window groups) 1-9.
# Each slot can have multiple "Nexus-Tabs".

SLOT="${1}"
SESSION=$(tmux display-message -p '#S')

if [[ -z "$SLOT" ]]; then
    echo "Usage: nxs-slot.sh <1-9>"
    exit 1
fi

# Find the last active window in this slot group
# We use tmux user-defined variables/hooks or just the first window for now
TARGET_WIN=$(tmux list-windows -t "$SESSION" -F '#I' | grep "^${SLOT}:" | head -1)

if [[ -n "$TARGET_WIN" ]]; then
    tmux select-window -t "$TARGET_WIN"
else
    # Optionally: Trigger a creation of a new window in the slot
    # tmux new-window -t "$SESSION" -n "${SLOT}:1"
    echo "Slot $SLOT is empty."
fi
