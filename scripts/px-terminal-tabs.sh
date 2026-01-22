#!/bin/bash
# px-terminal-tabs.sh - Manage multiple shells within a single tmux pane area
# Using tmux windows as "tabs" for a specific pane is complex, 
# so we use a sub-session or just simple pane swapping.

ACTION="$1"
SESSION_ID=$(tmux display-message -p '#S')
# Target the bottom terminal area (usually Pane 3)
PANE_TARGET=$(tmux display-message -p '#P')

case "$ACTION" in
    new)
        # Create a new pane and immediately hide it or join it?
        # Simpler: just use standard tmux 'new-window' if it's a full tab, 
        # but the user wants "tabs for the tmux panes".
        
        # Implementation: We'll create a new tmux window in the background 
        # and swap it into the current pane's spot? No, too slow.
        
        # Better: use a dedicated 'shells' window and provide a switcher in the pane.
        tmux split-window -v -t "$PANE_TARGET" "/bin/zsh"
        ;;
    next)
        tmux select-pane -t :.+
        ;;
    prev)
        tmux select-pane -t :.-
        ;;
    *)
        echo "Usage: px-terminal-tabs [new|next|prev]"
        ;;
esac
