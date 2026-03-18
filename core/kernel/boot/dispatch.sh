#!/bin/bash

# --- Nexus Global Command Dispatcher ---
# Handles commands from the ':' prompt in TMUX
# UI command dispatcher (TMUX)

DEBUG_LOG="/tmp/nexus_dispatch_debug.log"

CMD="$1"
# SCRIPT_DIR is .../nexus-shell/core/kernel/boot
SCRIPT_DIR="$(cd -P "$(dirname "$0")" && pwd)"
export NEXUS_HOME="$(cd "$SCRIPT_DIR/../../../" && pwd)"
export NEXUS_CORE="$NEXUS_HOME/core"
export NEXUS_KERNEL="$NEXUS_CORE/kernel"
export NEXUS_ENGINE="$NEXUS_CORE/engine"
export NEXUS_UI="$NEXUS_CORE/ui"
export NEXUS_SERVICES="$NEXUS_CORE/services"
export NEXUS_BOOT="$NEXUS_KERNEL/boot"
export NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"

echo "$(date '+%H:%M:%S') === dispatch.sh invoked ===" >> "$DEBUG_LOG"
echo "$(date '+%H:%M:%S') CMD=$CMD NEXUS_HOME=$NEXUS_HOME" >> "$DEBUG_LOG"

# Load tools configuration
TOOLS_CONF="$NEXUS_HOME/tools.conf"
[[ -f "$TOOLS_CONF" ]] && source "$TOOLS_CONF"

# Binaries location
# NEXUS_BIN is now bin/ in project root
NEXUS_BIN_DIR="$NEXUS_HOME/bin"
export PATH="$NEXUS_BIN_DIR:$PATH"

# Export for child processes
export NEXUS_HOME NEXUS_CORE NEXUS_KERNEL NEXUS_ENGINE NEXUS_UI NEXUS_SERVICES NEXUS_BOOT NEXUS_STATE SOCKET_LABEL PROJECT_ROOT

# Resolve tmux command with socket isolation
TMUX_CMD="tmux"
if [[ -n "$SOCKET_LABEL" ]]; then
    TMUX_CMD="tmux -L $SOCKET_LABEL"
fi

# Determine project from session name
SESSION_NAME=$($TMUX_CMD display-message -p '#S' 2>/dev/null)
# Correctly strip _client_... suffix to get master project name
MASTER_SESSION="${SESSION_NAME%_client_*}"
PROJECT_NAME="${MASTER_SESSION#nexus_}"
export PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
NVIM_PIPE="${NEXUS_PIPE:-$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe}"

echo "$(date '+%H:%M:%S') SESSION=$SESSION_NAME PROJECT=$PROJECT_NAME" >> "$DEBUG_LOG"
echo "$(date '+%H:%M:%S') Calling dispatch_helper.py..." >> "$DEBUG_LOG"

# === Registry-Driven Dispatch ===
python3 "$NEXUS_ENGINE/api/dispatch_helper.py" "$CMD" "${@:2}" 2>>"$DEBUG_LOG"
EXIT_CODE=$?

echo "$(date '+%H:%M:%S') dispatch_helper.py returned $EXIT_CODE" >> "$DEBUG_LOG"

if [[ $EXIT_CODE -eq 100 ]]; then
    # internal:help — show the full help popup
    $TMUX_CMD display-popup -E -w 70% -h 85% "$NEXUS_BOOT/help.sh"
    exit 0
elif [[ $EXIT_CODE -eq 2 ]]; then
    # Preflight failed (e.g. dirty buffer check)
    exit 1
elif [[ $EXIT_CODE -eq 127 ]]; then
    # Unknown command - show fallback
    if [[ -n "$CMD" ]]; then
        $TMUX_CMD display-message "Unknown command: $CMD (try :help)"
    fi
    exit 0
else
    exit $EXIT_CODE
fi
