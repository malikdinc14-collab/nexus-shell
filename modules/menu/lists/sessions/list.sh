#!/bin/bash
# pillars/sessions/list.sh
# Pulse Provider for active tmux sessions

if ! command -v tmux &> /dev/null; then
    echo '{"label": "Tmux not found", "type": "DISABLED", "payload": "NONE"}'
    exit 1
fi

tmux list-sessions -F '#{session_name}' | while read -r session; do
    # Get window count as telemetry
    win_count=$(tmux list-windows -t "$session" | wc -l | xargs)
    # Get active window name
    active_win=$(tmux display-message -p -t "$session" '#{window_name}')
    
    label="📟 $session ($win_count w)"
    description="Active: $active_win"
    
    # Output JSON object per session
    printf '{"label": "%s", "type": "ACTION", "payload": "tmux attach -t %s", "description": "%s", "icon": "📟"}\n' \
        "$label" "$session" "$description"
done
