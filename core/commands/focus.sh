#!/usr/bin/env bash
# core/commands/focus.sh
# Toggles the zoom (focus) state of the current Tmux pane.

SESSION_ID=$(tmux display-message -p '#S' 2>/dev/null)

# Toggle zoom
tmux resize-pane -Z

# Update Telemetry if zoomed
is_zoomed=$(tmux display-message -p '#{window_zoomed_flag}')

if [[ "$is_zoomed" == "1" ]]; then
    tmux display-message "Focus Mode: ACTIVE"
else
    tmux display-message "Focus Mode: DEACTIVATED"
fi
