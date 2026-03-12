#!/bin/bash

# --- Nexus Supervisor: SIMPLIFIED ROBUST EDITION ---
# Enforces stability through "Session-First" logic.

set -e

# 0. Early State Cleanup (Before any session checks)
# This ensures a clean slate for critical components like the nvim pipe.
# Note: NEXUS_STATE is not yet defined, so we use the explicit path.
rm -rf "/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe" 2>/dev/null

# 1. Identity Guard (Recursive/Re-entry Prevention)
if [[ -n "$NEXUS_STATION_ACTIVE" ]]; then
    echo "[!] ERROR: Station already active in this shell." >&2
    exit 109
fi

if [[ -n "$TMUX" ]]; then
    CURRENT_SESSION=$(tmux display-message -p '#S' 2>/dev/null || echo "unknown")
    if [[ "$CURRENT_SESSION" == nexus_* ]]; then
        echo "[!] ERROR: Recursive Nexus detected. You are already inside '$CURRENT_SESSION'." >&2
        echo "    Opening a station from within a station is prohibited to prevent recursion." >&2
        exit 110
    fi
fi

# 1.1 Process Genealogy Guard (Detect nested nxs calls)
if [[ -n "$NEXUS_BOOT_IN_PROGRESS" ]]; then
    echo "[!] ERROR: Circular boot detected. Aborting." >&2
    exit 111
fi
export NEXUS_BOOT_IN_PROGRESS=1

# 2. Physical Path Resolution (Follow symlinks to find Nexus Home)
REAL_PATH="$0"
while [ -h "$REAL_PATH" ]; do
    DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"
    REAL_PATH="$(readlink "$REAL_PATH")"
    [[ $REAL_PATH != /* ]] && REAL_PATH="$DIR/$REAL_PATH"
done
# SCRIPT_DIR is .../nexus-shell/core/boot
SCRIPT_DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"
export NEXUS_HOME="$(cd "$SCRIPT_DIR/../../" && pwd)"
export NEXUS_CORE="$NEXUS_HOME/core"
export NEXUS_SCRIPTS="$NEXUS_CORE/boot"

# PREPEND NEXUS BIN TO PATH (Critical for isolated modules)
export PATH="$HOME/.nexus-shell/bin:$PATH"

# 3. Environment Context
# Identify Project Root Early
PROJECT_ARG=""
for arg in "$@"; do
    [[ "$arg" != -* ]] && PROJECT_ARG="$arg" && break
done

PROJECT_ROOT="${PROJECT_ARG:-$(pwd)}"
PROJECT_ROOT="$(cd -- "$PROJECT_ROOT" && pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"

# 4. Tiered Configuration Loading (Clean Slate V1)
echo "[*] Loading Workspace Configuration..."
# Use Python helper to merge settings.yaml and .nexus.yaml
eval "$(python3 "$NEXUS_CORE/api/config_helper.py")"

# Apply Overrides from Flags (CLI Priority)
# By default, we always try to restore the slot's saved state first.
COMPOSITION="${NEXUS_COMPOSITION:-__saved_session__}"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --composition|-c) COMPOSITION="$2"; shift 2 ;;
        *) shift ;; 
    esac
done

SESSION_ID="nexus_$PROJECT_NAME"

# Resolve Configuration Path (Detect Layout)
if [[ -f "$HOME/.config/nexus-shell/config/keybinds.conf" ]]; then
    NEXUS_CONFIG_DIR="$HOME/.config/nexus-shell"
    TMUX_CONF="$NEXUS_CONFIG_DIR/tmux/nexus.conf"
else
    NEXUS_CONFIG_DIR="$NEXUS_HOME"
    TMUX_CONF="$NEXUS_CONFIG_DIR/config/tmux/nexus.conf"
fi

echo -e "\033[1;36m[*] INITIALIZING STATION: $PROJECT_NAME\033[0m"
echo "    Layout: $COMPOSITION"
echo "    Session: $SESSION_ID"

# 4.5 Load Legacy tools.conf (Backwards Compatibility)
TOOLS_CONF="$NEXUS_CONFIG_DIR/tools.conf"
[[ ! -f "$TOOLS_CONF" ]] && TOOLS_CONF="$(dirname "$NEXUS_CONFIG_DIR")/tools.conf"
if [[ -f "$TOOLS_CONF" ]]; then
    source "$TOOLS_CONF"
fi

# Tool Defaults (Configuration Hierarchy)
# Priority: 1. Flags (N/A yet) 2. .nexus.yaml 3. tools.conf 4. Global defaults
export NEXUS_EDITOR="${NEXUS_EDITOR:-nvim}"
export NEXUS_FILES="${NEXUS_FILES:-yazi}"
export NEXUS_CHAT="${NEXUS_CHAT:-opencode}"
MENU_BIN="$NEXUS_HOME/modules/menu/bin/nexus-menu"
ROUTER_BIN="$NEXUS_CORE/exec/router.sh"

# Build isolated state directory
export PX_STATE_DIR="/tmp/nexus_$(whoami)/$PROJECT_NAME/parallax"
mkdir -p "$PX_STATE_DIR"

# Build absolute command strings for the Architect
NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe"
mkdir -p "$(dirname "$NVIM_PIPE")"
export EDITOR_CMD="$NEXUS_EDITOR"
[[ "$NEXUS_EDITOR" == *"nvim"* ]] && export EDITOR_CMD="$NEXUS_EDITOR --listen $NVIM_PIPE"
export PARALLAX_CMD="PX_STATE_DIR=$PX_STATE_DIR $MENU_BIN"
export HAS_CHAT=true HAS_FILES=true

# 5. Mandatory State Reset & Initialization
# DISCOVERY: Do not kill-server. We want multi-window support.
STATION_EXISTS=$(tmux has-session -t "$SESSION_ID" 2>/dev/null && echo "yes" || echo "no")

# Initialize Kernel State
"$NEXUS_CORE/api/station_manager.sh" "$PROJECT_NAME" init

if [[ "$STATION_EXISTS" == "yes" ]]; then
    echo "[*] Station already exists for $PROJECT_NAME."
    
    # 1. Find the lowest available window index (0-9)
    MAX_WINDOWS=10
    WINDOW_IDX=-1
    
    # Build a string of currently used window indices
    USED_WINDOWS=$(tmux list-windows -t "$SESSION_ID" -F '#{window_index}')
    
    for ((i=1; i<MAX_WINDOWS; i++)); do
        if ! echo "$USED_WINDOWS" | grep -q "^$i$"; then
            WINDOW_IDX=$i
            break
        fi
    done
    
    if [[ $WINDOW_IDX -eq -1 ]]; then
         echo "[!] CRITICAL: Window limit ($MAX_WINDOWS) reached for this project." >&2
         exit 112
    fi
else
    # Create new session
    tmux new-session -d -s "$SESSION_ID" -x "$(tput cols)" -y "$(tput lines)"
    WINDOW_IDX=1
fi

CLIENT_SESSION="${SESSION_ID}"

# PHASE 4: Core Orchestration (HUD)
if [[ -f "$NEXUS_HOME/core/services/hud_service.sh" ]]; then
    "$NEXUS_HOME/core/services/hud_service.sh" start
fi

if ! tmux has-session -t "$SESSION_ID:HUD" 2>/dev/null; then
    tmux new-window -d -t "$SESSION_ID:10" -n "HUD" -c "$PROJECT_ROOT" "$NEXUS_HOME/core/hud/renderer.sh"
fi

rm -rf "/tmp/nexus_$(whoami)/$PROJECT_NAME/pipes"
mkdir -p "/tmp/nexus_$(whoami)/$PROJECT_NAME/pipes"
# sleep 0.5 # Reduced sleep

# 6. (Replaced by earlier atomic creation block)

# 7. Global Server Options
tmux set-option -gs exit-empty off
tmux set-option -gs exit-unattached off

# 8. Propagate Environment to Server (Global)
tmux set-environment -g NEXUS_HOME "$NEXUS_HOME"
tmux set-environment -g NEXUS_CORE "$NEXUS_CORE"
tmux set-environment -g NEXUS_BOOT "$NEXUS_CORE/boot"
tmux set-environment -g NEXUS_SCRIPTS "$NEXUS_CORE/boot"

# Propagate Environment to Session (Local)
tmux set-environment -t "$SESSION_ID" NEXUS_STATION_ACTIVE 1
tmux set-environment -t "$SESSION_ID" NEXUS_PROJECT "$PROJECT_NAME"
tmux set-environment -t "$SESSION_ID" NEXUS_CONFIG "$NEXUS_CONFIG_DIR"
tmux set-environment -t "$SESSION_ID" EDITOR_CMD "$EDITOR_CMD"
tmux set-environment -t "$SESSION_ID" PARALLAX_CMD "$PARALLAX_CMD"
tmux set-environment -t "$SESSION_ID" NEXUS_FILES "$NEXUS_FILES"
tmux set-environment -t "$SESSION_ID" NEXUS_CHAT "$NEXUS_CHAT"

# 9. Build the Layout (Synchronous & Staggered)
echo "[*] Building Station Architecture in Slot $WINDOW_IDX..."
"$NEXUS_CORE/layout/layout_engine.sh" "$SESSION_ID:$WINDOW_IDX" "$COMPOSITION" "$SESSION_ID" "$PROJECT_ROOT"

# Restore active theme from persistent state
if [[ -x "$NEXUS_SCRIPTS/theme.sh" ]]; then
    CURRENT_THEME=$("$NEXUS_SCRIPTS/theme.sh" current)
    "$NEXUS_SCRIPTS/theme.sh" apply "$CURRENT_THEME" >/dev/null 2>&1 || true
fi

# 10. Success Handover
echo -e "\033[1;32m[*] Station Solidified. Attaching...\033[0m"
export NEXUS_STATION_ACTIVE=1

# Assertion: Terminal Lifecycle Invariant (Negative Space)
# The station MUST NOT exist without an active observer (terminal window).
# We anchor the session's life to the client's attachment state.
# tmux set-hook -t "$SESSION_ID" client-detached "kill-session -t '$SESSION_ID'"
# Ensure the client session focuses the window we just built
tmux select-window -t "$CLIENT_SESSION:$WINDOW_IDX"

exec tmux attach-session -t "$CLIENT_SESSION"
