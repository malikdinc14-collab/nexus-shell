#!/bin/bash

# --- Nexus Global Command Dispatcher ---
# Handles commands from the ':' prompt in TMUX
# UI command dispatcher (TMUX)

CMD="$1"
NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
NEXUS_BIN="$NEXUS_HOME/bin"
NEXUS_CORE="$NEXUS_HOME/core"
NEXUS_BOOT="$NEXUS_CORE/boot"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"

# Load tools configuration
TOOLS_CONF="$NEXUS_HOME/tools.conf"
[[ -f "$TOOLS_CONF" ]] && source "$TOOLS_CONF"

# Binaries location
NEXUS_BIN_DIR="${NEXUS_BIN:-$HOME/.nexus-shell/bin}"
export PATH="$NEXUS_BIN_DIR:$PATH"

# Parallax Configuration Defaults
NEXUS_PX_UI="${NEXUS_PX_UI:-tmux}" # options: tmux, gum

# Determine project from session name
SESSION_NAME=$(tmux display-message -p '#S')
PROJECT_NAME=${SESSION_NAME#nexus_}
NVIM_PIPE="${NEXUS_PIPE:-$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe}"

# === Registry-Driven Dispatch ===
# Try to handle via Command Registry
python3 "$NEXUS_CORE/api/dispatch_helper.py" "$CMD" "${@:2}"
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    exit 0
elif [[ $EXIT_CODE -eq 100 ]]; then
    # internal:help handle via tmux popup for better formatting
    tmux display-popup -E -w 60% -h 70% "python3 $NEXUS_CORE/api/dispatch_helper.py --help-only"
    exit 0
elif [[ $EXIT_CODE -eq 1 ]]; then
    # Preflight failed (e.g. dirty buffer check)
    exit 1
fi

# === Fallback (Agent & External) ===
if [[ "$CMD" == "!"* ]]; then
    # Query the agent directly
    QUERY="${CMD#!}"
    "$NEXUS_CORE/api/px-bridge-agent.sh" "$QUERY"
elif [[ -n "$CMD" ]]; then
    # Try as a nexus command, if fails, send to agent as general query
    # (In testing phase, we treat any unknown :command as a query)
    "$NEXUS_CORE/api/px-bridge-agent.sh" "$CMD"
fi
