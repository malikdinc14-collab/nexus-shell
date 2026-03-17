#!/bin/bash
# core/kernel/boot/pane_wrapper.sh
# --- Nexus Pane Wrapper ---
# Indestructible viewports: runs a command and falls back to shell on exit.

# 1. Zero-Entropy Path Resolution
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_SCRIPTS="$SCRIPT_DIR"
export ZDOTDIR="$NEXUS_HOME/config/zsh"

# 2. Process Containment: Cleanup children on exit
trap 'pkill -P $$ 2>/dev/null; exit 0' SIGTERM SIGHUP SIGINT

COMMAND="$@"

# Execute the command once
if [[ -n "$COMMAND" ]]; then
    eval "$COMMAND"
fi

# Tool exited — drop to an interactive shell so the pane stays alive
# exec replaces the wrapper process with zsh
exec /bin/zsh -i
