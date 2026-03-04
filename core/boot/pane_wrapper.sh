#!/bin/bash

# --- Nexus Pane Wrapper ---
# Indestructible viewports: runs a command and auto-restarts it on exit.

# 1. Zero-Entropy Path Resolution
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_SCRIPTS="$SCRIPT_DIR"

# 2. Unified Logging
LOG="/tmp/nexus_station.log"
echo "[$(date)] PANE_WRAPPER PID:$$ STARTING CMD: $*" >> "$LOG"

# 3. Process Containment: Cleanup children on exit
trap 'pkill -P $$; exit 0' SIGTERM SIGINT SIGHUP

COMMAND="$@"

# Main loop: run the command, and if it exits, offer to restart it
while true; do
    if [[ -n "$COMMAND" ]]; then
        echo "[$(date)] PANE_WRAPPER PID:$$ RUNNING: $COMMAND" >> "$LOG"
        eval "$COMMAND"
        EXIT_CODE=$?
        
        # If the command exited cleanly (0), just restart it silently
        # If it crashed, show a brief message before restarting
        if [[ $EXIT_CODE -ne 0 ]]; then
            echo ""
            echo -e "\033[1;33m  [Nexus] Process exited (code $EXIT_CODE).\033[0m"
            echo -e "  Restarting in 2 seconds... (press \033[1;36mCtrl-C\033[0m to drop to shell)"
            sleep 2
        else
            # Clean exit — tiny pause to avoid spin loop, then restart
            sleep 0.3
        fi
    else
        # No command given — just run a shell
        /bin/zsh -i
    fi
done
