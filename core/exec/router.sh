#!/usr/bin/env zsh
# core/exec/router.sh
# The Execution Router for Nexus
# Intercepts the pure STDOUT of the Menu and routes it to the specific environment action.

# Read from STDIN if piped, otherwise take $1
if [[ -p /dev/stdin ]]; then
    read -r PAYLOAD
else
    PAYLOAD="$1"
fi

# If no payload, do nothing
if [[ -z "$PAYLOAD" ]]; then
    exit 0
fi

# Split the payload on the first pipe
TYPE="${PAYLOAD%%|*}"
DATA="${PAYLOAD#*|}"

# Helper to find a pane by its exact title
get_pane_by_title() {
    local target_title="$1"
    tmux list-panes -F "#{pane_id} #{pane_title}" | grep -E " $target_title$" | head -n 1 | awk '{print $1}'
}

# Find commonly used panes
EDITOR_PANE=$(get_pane_by_title "editor")
TERM_PANE=$(get_pane_by_title "terminal")

case "$TYPE" in
    PLACE)
        # Directory Navigation
        if [[ -n "$TMUX" ]]; then
            if [[ -n "$TERM_PANE" ]]; then
                tmux send-keys -t "$TERM_PANE" "cd \"$DATA\" && clear" Enter
            else
                tmux send-keys "cd \"$DATA\" && clear" Enter
            fi
        else
            cd "$DATA" || exit
            zsh
        fi
        ;;

    ACTION)
        # Execute the string (script or command)
        if [[ "$DATA" == :workspace* ]]; then
            "${NEXUS_HOME}/core/commands/workspace.sh" ${DATA#*:workspace }
        elif [[ "$DATA" == :profile* ]]; then
            "${NEXUS_HOME}/core/commands/profile.sh" ${DATA#*:profile }
        elif [[ "$DATA" == :debug* ]]; then
            "${NEXUS_HOME}/core/exec/dap_handler.sh" ${DATA#*:debug }
        elif [[ -n "$TMUX" ]]; then
            if [[ -n "$TERM_PANE" ]]; then
                tmux send-keys -t "$TERM_PANE" "$DATA" Enter
            else
                tmux send-keys "$DATA" Enter
            fi
        else
            eval "$DATA"
            echo -e "\n\033[1;30m>>> Press Enter to return to menu\033[0m"
            read -r
        fi
        ;;

    NOTE|DOC)
        # Open in Editor or Viewer
        if [[ -n "$TMUX" ]]; then
            if [[ -n "$EDITOR_PANE" ]]; then
                # Send escape to ensure we are in normal mode, then open the file
                tmux send-keys -t "$EDITOR_PANE" Escape Escape ":e $DATA" Enter
            else
                # Popup window for the note if no editor exists
                tmux display-popup -w 80% -h 80% -E "glow \"$DATA\" -p || less \"$DATA\""
            fi
        else
            if command -v glow &>/dev/null; then
                glow "$DATA" -p
            else
                cat "$DATA"
            fi
            echo -e "\n\033[1;30m>>> Press Enter to return to menu\033[0m"
            read -r
        fi
        ;;

    MODEL|AGENT)
        # Open the AI Agent connection 
        echo -e "\033[1;34m🤖 Connecting to $DATA...\033[0m"
        if command -v px-agent &>/dev/null; then
            px-agent chat "$DATA"
        else
            echo "px-agent not found in path."
            sleep 2
        fi
        ;;

    PROJECT)
        # Switch into a project workspace
        echo "Starting Workspace: $DATA"
        cd "$DATA" || exit
        zsh
        ;;
        
    RAW)
        # Just echo it
        echo "$DATA"
        ;;

    *)
        echo "Unknown Payload Type: $TYPE"
        echo "Data: $DATA"
        sleep 2
        ;;
esac
