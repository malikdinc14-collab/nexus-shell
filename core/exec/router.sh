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

# Determine Execution Context
# If NXS_STRICT_LOCAL is set, we never jump.
STRICT_LOCAL="${NXS_STRICT_LOCAL:-false}"

case "$TYPE" in
    PLACE)
        # Directory Navigation
        if [[ "$STRICT_LOCAL" == "false" && -n "$TERM_PANE" ]]; then
            tmux send-keys -t "$TERM_PANE" "cd \"$DATA\" && clear" Enter
        else
            cd "$DATA" || exit
            clear
            exec zsh -i
        fi
        ;;

    ACTION)
        # Execute the string (script or command)
        if [[ "$DATA" == :* ]]; then
            # Handle special Nexus commands
            local COMMAND_TYPE="${DATA%% *}"
            local COMMAND_ARGS="${DATA#* }"
            case "$COMMAND_TYPE" in
                ":workspace") "${NEXUS_HOME}/core/commands/workspace.sh" "$COMMAND_ARGS" ;;
                ":profile")   "${NEXUS_HOME}/core/commands/profile.sh" load "$COMMAND_ARGS" ;;
                ":focus")     "${NEXUS_HOME}/core/commands/focus.sh" ;;
                ":debug")     "${NEXUS_HOME}/core/exec/dap_handler.sh" "$COMMAND_ARGS" ;;
                *)
                    # execute locally
                    eval "$DATA"
                    ;;
            esac
        elif [[ "$STRICT_LOCAL" == "false" && -n "$TERM_PANE" ]]; then
            tmux send-keys -t "$TERM_PANE" "$DATA" Enter
        else
            # Execute in current pane
            eval "$DATA"
        fi
        ;;

    NOTE|DOC)
        # Open in Editor or Viewer
        if [[ "$STRICT_LOCAL" == "false" && -n "$EDITOR_PANE" ]]; then
            # Send escape to ensure we are in normal mode, then open the file
            tmux send-keys -t "$EDITOR_PANE" Escape Escape ":e $DATA" Enter
        else
            # execute in current pane
            ${NEXUS_EDITOR:-nvim} "$DATA"
        fi
        ;;

    MODEL|AGENT)
        # Open the AI Agent connection 
        echo -e "\033[1;34m🤖 Connecting to $DATA...\033[0m"
        if command -v px-agent &>/dev/null; then
            px-agent chat "$DATA"
        else
            # fallback to direct bin
            "$NEXUS_HOME/modules/agents/bin/px-agent" chat "$DATA"
        fi
        ;;

    PROJECT)
        # Switch into a project workspace
        echo "Starting Workspace: $DATA"
        cd "$DATA" || exit
        exec zsh -i
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
