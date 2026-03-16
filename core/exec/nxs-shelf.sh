#!/bin/bash
# core/exec/nxs-shelf.sh
# Manages the "Shelf" (Hidden Panes) using Tmux break-pane/join-pane.

ACTION="$1"
SESSION_ID="${SESSION_ID:-$(tmux display-message -p '#S')}"
RESERVOIR="NEXUS_SHELF"

# Ensure Reservoir window exists
if ! tmux has-session -t "$SESSION_ID:$RESERVOIR" 2>/dev/null; then
    tmux new-window -d -t "$SESSION_ID" -n "$RESERVOIR" "tail -f /dev/null"
fi

case "$ACTION" in
    stow)
        # Move current pane to the shelf
        PANE_ID=$(tmux display-message -p '#{pane_id}')
        PANE_NAME=$(tmux display-message -p '#{@nexus_tab_name}')
        [[ -z "$PANE_NAME" ]] && PANE_NAME=$(tmux display-message -p '#{pane_current_command}')
        
        # Don't stow if it's the last pane in the main window (optional guard)
        PANE_COUNT=$(tmux list-panes | wc -l)
        if [[ "$PANE_COUNT" -le 1 ]]; then
            tmux display-message "Cannot stow the last remaining pane."
            exit 1
        fi

        tmux display-message "Shelving: $PANE_NAME"
        tmux break-pane -d -s "$PANE_ID" -t "$SESSION_ID:$RESERVOIR"
        ;;

    list)
        # List panes on the shelf for the menu
        # Output: JSON object per line
        tmux list-panes -t "$SESSION_ID:$RESERVOIR" -F '#{pane_id}	#{pane_current_command}	#{@nexus_tab_name}' | while read -r line; do
            ID=$(echo "$line" | cut -f1)
            CMD=$(echo "$line" | cut -f2)
            NAME=$(echo "$line" | cut -f3)
            [[ -z "$NAME" ]] && NAME="$CMD"
            
            # Output as JSON for the professional protocol
            printf '{"label": "📦 %s", "type": "SHELF_ITEM", "payload": "%s"}\n' "$NAME" "$ID"
        done
        ;;

    recall)
        # Pull a pane from the shelf back into the current window
        TARGET_PANE="$2"
        CURRENT_PANE=$(tmux display-message -p '#{pane_id}')
        
        if [[ -z "$TARGET_PANE" ]]; then
            echo "Usage: nxs-shelf recall <pane_id>"
            exit 1
        fi

        # Join the shelf pane to the current window
        # We split the current pane to make room
        tmux join-pane -s "$TARGET_PANE" -t "$CURRENT_PANE"
        ;;

    *)
        echo "Usage: nxs-shelf {stow|list|recall <id>}"
        exit 1
        ;;
esac
