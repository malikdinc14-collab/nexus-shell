#!/bin/bash

# --- Nexus Supervisor: SIMPLIFIED ROBUST EDITION ---
# Enforces stability through "Session-First" logic.

set -e

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
# Handle flags (e.g., --composition)
COMPOSITION="vscodelike"
PROJECT_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --composition) COMPOSITION="$2"; shift 2 ;;
        -c) COMPOSITION="$2"; shift 2 ;;
        -*) shift ;; # Unknown flag
        *) PROJECT_ARG="$1"; shift ;;
    esac
done

PROJECT_ROOT="${PROJECT_ARG:-$(pwd)}"
PROJECT_ROOT="$(cd -- "$PROJECT_ROOT" && pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
SESSION_ID="nexus_$PROJECT_NAME"

# Resolve Configuration Path (Detect Layout)
if [[ -f "$HOME/.config/nexus-shell/config/keybinds.conf" ]]; then
    # Installed Layout
    NEXUS_CONFIG_DIR="$HOME/.config/nexus-shell"
    TMUX_CONF="$NEXUS_CONFIG_DIR/tmux/nexus.conf"
else
    # Source/Dev Layout (current layout)
    NEXUS_CONFIG_DIR="$NEXUS_HOME"
    TMUX_CONF="$NEXUS_CONFIG_DIR/config/tmux/nexus.conf"
fi

echo -e "\033[1;36m[*] INITIALIZING STATION: $PROJECT_NAME\033[0m"
echo "    Layout: $COMPOSITION"
echo "    Session: $SESSION_ID"

# 4. Load Tool Configurations
TOOLS_CONF="$NEXUS_CONFIG_DIR/tools.conf"
# Fallback to config dir parent if in source mode
[[ ! -f "$TOOLS_CONF" ]] && TOOLS_CONF="$(dirname "$NEXUS_CONFIG_DIR")/tools.conf" # Source mode tools.conf location?
# Actually source vs installed tools.conf might differ too.
# In source: no tools.conf usually.
# In install: ~/.config/nexus-shell/tools.conf

if [[ -f "$TOOLS_CONF" ]]; then
    source "$TOOLS_CONF"
fi
if [[ -f "$TOOLS_CONF" ]]; then
    source "$TOOLS_CONF"
fi

# Tool Defaults & Command Construction
NEXUS_EDITOR="${NEXUS_EDITOR:-nvim}"
NEXUS_FILES="${NEXUS_FILES:-yazi}"
NEXUS_CHAT="${NEXUS_CHAT:-opencode}"
PARALLAX_BIN="$HOME/.parallax/bin/parallax"

# Build absolute command strings for the Architect
NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe"
export EDITOR_CMD="$NEXUS_EDITOR"
[[ "$NEXUS_EDITOR" == *"nvim"* ]] && export EDITOR_CMD="$NEXUS_EDITOR --listen $NVIM_PIPE"
export PARALLAX_CMD="PX_NEXUS_MODE=1 PX_NEXUS_SESSION=$SESSION_ID $PARALLAX_BIN --nexus"
export NEXUS_FILES NEXUS_CHAT
export HAS_CHAT=true HAS_FILES=true

# 5. Mandatory State Reset & Initialization
# DISCOVERY: Do not kill-server. We want multi-window support.
STATION_EXISTS=$(tmux has-session -t "$SESSION_ID" 2>/dev/null && echo "yes" || echo "no")

# Initialize Kernel State
"$NEXUS_CORE/api/station_manager.sh" "$PROJECT_NAME" init

if [[ "$STATION_EXISTS" == "yes" ]]; then
    echo "[*] Station already exists for $PROJECT_NAME."
    # Generate a unique session ID for this window (e.g., suffix _2, _3)
    # MAX_SESSIONS safety guard
    MAX_SESSIONS=10
    i=2
    while tmux has-session -t "${SESSION_ID}_$i" 2>/dev/null; do
        if [[ $i -ge $MAX_SESSIONS ]]; then
             echo "[!] CRITICAL: Session limit ($MAX_SESSIONS) reached for this project." >&2
             echo "    Is there a recursive loop in your .zshrc calling 'nxs'?" >&2
             exit 112
        fi
        ((i++))
    done
    SESSION_ID="${SESSION_ID}_$i"
    echo "[*] Opening secondary observer: $SESSION_ID"
fi

rm -rf "/tmp/nexus_$(whoami)/$PROJECT_NAME/pipes"
mkdir -p "/tmp/nexus_$(whoami)/$PROJECT_NAME/pipes"
# sleep 0.5 # Reduced sleep

# 6. THE ATOMIC INVARIANT: Session-First Creation
tmux -f "$TMUX_CONF" new-session -d -s "$SESSION_ID" -n "workspace" -c "$PROJECT_ROOT" -x 200 -y 50 "/bin/zsh"

# 7. Global Server Options
tmux set-option -gs exit-empty off
tmux set-option -gs exit-unattached off

# 8. Propagate Environment to Session
tmux set-environment -t "$SESSION_ID" NEXUS_STATION_ACTIVE 1
tmux set-environment -t "$SESSION_ID" NEXUS_PROJECT "$PROJECT_NAME"
tmux set-environment -t "$SESSION_ID" NEXUS_HOME "$NEXUS_HOME"
tmux set-environment -t "$SESSION_ID" NEXUS_CONFIG "$NEXUS_CONFIG_DIR"
tmux set-environment -t "$SESSION_ID" EDITOR_CMD "$EDITOR_CMD"
tmux set-environment -t "$SESSION_ID" PARALLAX_CMD "$PARALLAX_CMD"
tmux set-environment -t "$SESSION_ID" NEXUS_FILES "$NEXUS_FILES"
tmux set-environment -t "$SESSION_ID" NEXUS_CHAT "$NEXUS_CHAT"

# 9. Build the Layout (Synchronous & Staggered)
echo "[*] Building Station Architecture..."
"$NEXUS_CORE/layout/layout_engine.sh" "$SESSION_ID:0" "$COMPOSITION" "$SESSION_ID" "$PROJECT_ROOT"

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

exec tmux attach-session -t "$SESSION_ID"
