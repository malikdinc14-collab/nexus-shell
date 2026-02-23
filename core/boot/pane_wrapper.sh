#!/bin/bash

# --- Nexus Pane Wrapper ---
# Indestructible viewports with FZF tool switching

# 1. Zero-Entropy Path Resolution
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_SCRIPTS="$SCRIPT_DIR"

# 2. Unified Logging
LOG="/tmp/nexus_station.log"
echo "[$(date)] PANE_WRAPPER PID:$$ STARTING CMD: $*" >> "$LOG"

# 3. Invariant Assertion: Environment Integrity
if [[ -z "$TMUX" && -z "$TERM_PROGRAM" && ! -t 0 ]]; then
    echo "[!] INVARIANT VIOLATION: Execution without TTY or TMUX context." >> "$LOG"
    exit 101 
fi

# 4. Process Containment: Cleanup children on exit
trap 'pkill -P $$; exit 0' SIGTERM SIGINT SIGHUP

COMMAND="$@"
SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null || echo "detached")

# 5. Graceful Guard
show_hub() {
    clear
    # Ensure we don't spin if there's no TTY
    if [[ ! -t 0 ]]; then
        echo "[!] PANE WAITING FOR ATTACHMENT..."
        while [[ ! -t 0 ]]; do sleep 2; done
    fi

    echo -e "\033[1;36m[ NEXUS PANE HUB ]\033[0m"
    echo "──────────────────────────────"
    echo "Project: $NEXUS_PROJECT"
    echo ""
    
    local menu_items="editor|Editor\nrender|Render\nshell|Terminal\nfiles|Files\nchat|AI Chat\ngit|Git\nexit|EXIT STATION"
    
    selection=$(echo -e "$menu_items" | fzf --reverse --height=50% --border --header="Choose Tool")
    key="${selection%%|*}"
    
    case "$key" in
        "editor") COMMAND="$EDITOR_CMD" ;;
        "shell")  COMMAND="/bin/zsh -i" ;;
        "files")  COMMAND="$NEXUS_FILES" ;;
        "chat")   COMMAND="$NEXUS_CHAT" ;;
        "exit")   tmux kill-session -t "$SESSION_NAME"; exit 0 ;;
        *)        COMMAND="/bin/zsh -i" ;;
    esac
}

run_tool() {
    [[ -z "$COMMAND" ]] && return
    echo "[$(date)] PANE_WRAPPER PID:$$ RUNNING: $COMMAND" >> "$LOG"
    eval "$COMMAND"
}

# Main loop
if [[ -n "$COMMAND" ]]; then
    run_tool
fi

while true; do
    show_hub
    run_tool
    sleep 1
done
