#!/bin/bash

# --- Nexus Supervisor: SIMPLIFIED ROBUST EDITION ---
# Enforces stability through "Session-First" logic.

set -e

# 1. Identity Guard (Recursive Lock)
if [[ -n "$NEXUS_STATION_ACTIVE" ]]; then
    echo "[!] ERROR: Station already active in this shell." >&2
    exit 109
fi

# 2. Physical Path Resolution (Follow symlinks to find scripts)
REAL_PATH="$0"
while [ -h "$REAL_PATH" ]; do
    DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"
    REAL_PATH="$(readlink "$REAL_PATH")"
    [[ $REAL_PATH != /* ]] && REAL_PATH="$DIR/$REAL_PATH"
done
SCRIPT_DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"
export NEXUS_SCRIPTS="$SCRIPT_DIR"
NEXUS_CONFIG_DIR="$(dirname "$SCRIPT_DIR")"

# 3. Environment Context
PROJECT_ROOT="${1:-$(pwd)}"
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
SESSION_ID="nexus_$PROJECT_NAME"
TMUX_CONF="$NEXUS_CONFIG_DIR/tmux/nexus.conf"

echo -e "\033[1;36m[*] INITIALIZING STATION: $PROJECT_NAME\033[0m"

# 4. Load Tool Configurations
TOOLS_CONF="$NEXUS_CONFIG_DIR/tools.conf"
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

# 5. Mandatory State Reset
tmux kill-server 2>/dev/null || true
rm -rf "/tmp/nexus_$(whoami)/pipes"
mkdir -p "/tmp/nexus_$(whoami)/pipes"
sleep 0.5

# 6. THE ATOMIC INVARIANT: Session-First Creation
tmux -f "$TMUX_CONF" new-session -d -s "$SESSION_ID" -n "workspace" -c "$PROJECT_ROOT" -x 200 -y 50 "/bin/zsh"

# 7. Global Server Options
tmux set-option -gs exit-empty off
tmux set-option -gs exit-unattached off

# 8. Propagate Environment to Session
tmux set-environment -t "$SESSION_ID" NEXUS_STATION_ACTIVE 1
tmux set-environment -t "$SESSION_ID" NEXUS_PROJECT "$PROJECT_NAME"
tmux set-environment -t "$SESSION_ID" NEXUS_CONFIG "$NEXUS_CONFIG_DIR"
tmux set-environment -t "$SESSION_ID" EDITOR_CMD "$EDITOR_CMD"
tmux set-environment -t "$SESSION_ID" PARALLAX_CMD "$PARALLAX_CMD"
tmux set-environment -t "$SESSION_ID" NEXUS_FILES "$NEXUS_FILES"
tmux set-environment -t "$SESSION_ID" NEXUS_CHAT "$NEXUS_CHAT"

# 9. Build the Layout (Synchronous & Staggered)
echo "[*] Building Station Architecture..."
"$SCRIPT_DIR/layout_engine.sh" "$SESSION_ID:0" "vscodelike" "$SESSION_ID" "$PROJECT_ROOT"

# 10. Success Handover
echo -e "\033[1;32m[*] Station Solidified. Attaching...\033[0m"
export NEXUS_STATION_ACTIVE=1

# Assertion: Terminal Lifecycle Invariant (Negative Space)
# The station MUST NOT exist without an active observer (terminal window).
# We anchor the session's life to the client's attachment state.
tmux set-hook -t "$SESSION_ID" client-detached "kill-session -t '$SESSION_ID'"

exec tmux attach-session -t "$SESSION_ID"
