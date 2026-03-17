#!/bin/bash
# core/kernel/exec/nxs-kill-pane.sh
# Intelligent pane closure for Nexus Shell

PANE_COUNT=$(tmux list-panes | wc -l)

if [[ "$PANE_COUNT" -gt 1 ]]; then
    tmux kill-pane
else
    # Check if there are other windows or sessions? 
    # For now, just prevent closing the last pane in a window to avoid accidental session death if it's the only one.
    tmux display-message "Nexus Guard: Cannot close the last pane."
fi
