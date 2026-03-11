#!/bin/bash

# --- Nexus Global Command Dispatcher ---
# Handles commands from the ':' prompt in TMUX
# UI command dispatcher (TMUX)

DEBUG_LOG="/tmp/nexus_dispatch_debug.log"

CMD="$1"
NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
NEXUS_BIN="$NEXUS_HOME/bin"
NEXUS_CORE="$NEXUS_HOME/core"
NEXUS_BOOT="$NEXUS_CORE/boot"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"

echo "$(date '+%H:%M:%S') === dispatch.sh invoked ===" >> "$DEBUG_LOG"
echo "$(date '+%H:%M:%S') CMD=$CMD NEXUS_HOME=$NEXUS_HOME" >> "$DEBUG_LOG"

# Load tools configuration
TOOLS_CONF="$NEXUS_HOME/tools.conf"
[[ -f "$TOOLS_CONF" ]] && source "$TOOLS_CONF"

# Binaries location
NEXUS_BIN_DIR="${NEXUS_BIN:-$HOME/.nexus-shell/bin}"
export PATH="$NEXUS_BIN_DIR:$PATH"

# Export for child processes
export NEXUS_HOME NEXUS_CORE NEXUS_BOOT NEXUS_STATE

# Determine project from session name
SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null)
PROJECT_NAME=${SESSION_NAME#nexus_}
export PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
NVIM_PIPE="${NEXUS_PIPE:-$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe}"

echo "$(date '+%H:%M:%S') SESSION=$SESSION_NAME PROJECT=$PROJECT_NAME" >> "$DEBUG_LOG"
echo "$(date '+%H:%M:%S') Calling dispatch_helper.py..." >> "$DEBUG_LOG"

# === Registry-Driven Dispatch ===
python3 "$NEXUS_CORE/api/dispatch_helper.py" "$CMD" "${@:2}" 2>>"$DEBUG_LOG"
EXIT_CODE=$?

echo "$(date '+%H:%M:%S') dispatch_helper.py returned $EXIT_CODE" >> "$DEBUG_LOG"

if [[ $EXIT_CODE -eq 100 ]]; then
    # internal:help — show the full help popup
    tmux display-popup -E -w 70% -h 85% "$NEXUS_BOOT/help.sh"
    exit 0
elif [[ $EXIT_CODE -eq 2 ]]; then
    # Preflight failed (e.g. dirty buffer check)
    exit 1
elif [[ $EXIT_CODE -eq 127 ]]; then
    # Unknown command - show fallback
    if [[ -n "$CMD" ]]; then
        tmux display-message "Unknown command: $CMD (try :help)"
    fi
    exit 0
else
    exit $EXIT_CODE
fi
