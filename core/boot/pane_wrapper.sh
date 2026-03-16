#!/bin/bash
# core/boot/pane_wrapper.sh
# --- Nexus Pane Wrapper ---
# Indestructible viewports: runs a command and falls back to shell on exit.

# 1. Zero-Entropy Path Resolution
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_SCRIPTS="$SCRIPT_DIR"
export ZDOTDIR="$NEXUS_HOME/config/zsh"

# 2. Process Containment: Cleanup children on exit
trap 'pkill -P $$ 2>/dev/null; exit 0' SIGTERM SIGHUP SIGINT

# 3. Execution with Debug Logging
COMMAND="$@"

if [[ -n "$COMMAND" ]]; then
    if [[ "$NEXUS_DEBUG" == "1" ]]; then
        LOG_FILE="/tmp/nexus_$(whoami)/$PROJECT_NAME/panes.log"
        echo "[$(date +%T)] Executing: $COMMAND" >> "$LOG_FILE"
        # We use a subshell to capture stderr without breaking interactive TUI stdout
        # However, 'eval' itself is tricky. We'll at least log the attempt.
        eval "$COMMAND" 2> >(tee -a "$LOG_FILE" >&2)
    else
        eval "$COMMAND"
    fi
fi

# Tool exited — drop to an interactive shell so the pane stays alive
# exec replaces the wrapper process with zsh
exec /bin/zsh -i
