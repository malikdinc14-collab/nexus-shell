#!/usr/bin/env zsh
# core/exec/router.sh
# The Execution Router for Nexus
# Intercepts the pure STDOUT of the Menu and routes it to the specific environment action.

PAYLOAD="$1"

# If no payload, do nothing
if [[ -z "$PAYLOAD" ]]; then
    exit 0
fi

# Split the payload on the first pipe
TYPE="${PAYLOAD%%|*}"
DATA="${PAYLOAD#*|}"

# Ensure we have our environment loaded
[[ -f "$PX_ENV_FILE" ]] && source "$PX_ENV_FILE"

# Log the routing decision
PX_LOG_FILE="/tmp/nxs-router-$(date +%s).log"
echo "ROUTING [$TYPE]: $DATA" >> "$PX_LOG_FILE"

case "$TYPE" in
    PLACE)
        # Directory Navigation
        # Just cd into it and start a new zsh shell if running directly, 
        # or sendkeys if we are in a tmux orchestrator mode
        if [[ -n "$TMUX" ]]; then
            tmux send-keys 'cd "'"$DATA"'" && clear' Enter
        else
            cd "$DATA" || exit
            zsh
        fi
        ;;

    ACTION)
        # Execute the string (script or command)
        if [[ -n "$TMUX" ]]; then
            # Spawn a new pane or just run it here
            tmux send-keys "$DATA\n"
        else
            eval "$DATA"
            echo -e "\n\033[1;30m>>> Press Enter to return to menu\033[0m"
            read -r
        fi
        ;;

    NOTE|DOC)
        # Open in Glowing Markdown Viewer or Editor
        if command -v glow &>/dev/null; then
            glow "$DATA" -p
        else
            cat "$DATA"
        fi
        echo -e "\n\033[1;30m>>> Press Enter to return to menu\033[0m"
        read -r
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
        # Since router is running inside nxs, we might just need to pass this up to the python launcher
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
