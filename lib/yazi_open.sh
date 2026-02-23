#!/usr/bin/env zsh

# --- Nexus Yazi-to-Editor Bridge ---
# Opens selected file from Yazi directly in the editor pane (no prompts)

FILE="$1"
[[ -z "$FILE" ]] && exit 0

NEXUS_CONFIG="${NEXUS_CONFIG:-$HOME/.config/nexus-shell}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
NEXUS_SCRIPTS="$NEXUS_CONFIG/scripts"

# Load tools config
TOOLS_CONF="$NEXUS_CONFIG/tools.conf"
[[ -f "$TOOLS_CONF" ]] && source "$TOOLS_CONF"

# --- Robust Environment Recovery ---
# If env vars are missing (Yazi sometimes strips them), grab them from tmux
# We get the session name first, then pull its environment
CUR_SESSION=$(tmux display-message -p '#S' 2>/dev/null)
if [[ -n "$CUR_SESSION" ]]; then
    # Pull session-specific environment variables
    eval "$(tmux show-environment -t "$CUR_SESSION" -s 2>/dev/null | grep -E 'NEXUS_|PX_NEXUS_')"
fi

# Fallback to global environment if session pull failed or was incomplete
if [[ -z "$NEXUS_PROJECT" ]]; then
    eval "$(tmux show-environment -s 2>/dev/null | grep -E 'NEXUS_|PX_NEXUS_')"
fi

# Resolve to absolute path
ABS_FILE=$(realpath "$FILE" 2>/dev/null || echo "$FILE")

# IF DIRECTORY: Tell Yazi to enter it and exit
if [[ -d "$ABS_FILE" ]]; then
    tmux send-keys -t "$TMUX_PANE" "enter"
    exit 0
fi

# Visual feedback
tmux display-message "Nexus Open: $ABS_FILE"

SESSION_NAME=$(tmux display-message -p '#S')
PROJECT_NAME=${NEXUS_PROJECT:-${SESSION_NAME#nexus_}}
NVIM_PIPE="${NEXUS_PIPE:-$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe}"
LAST_FILE="$NEXUS_STATE/last_path"
MODE_FILE="$NEXUS_STATE/editor_mode"
WRAPPER="$NEXUS_SCRIPTS/pane_wrapper.sh"

NEXUS_EDITOR="${NEXUS_EDITOR:-nvim}"

# Update state
mkdir -p "$NEXUS_STATE/pipes"
echo "$ABS_FILE" > "$LAST_FILE"

# Find editor pane
if [[ "${PX_NEXUS_EDITOR_PANE:- -1}" -ge 0 ]]; then
    EDITOR_PANE="$PX_NEXUS_EDITOR_PANE"
else
    EDITOR_PANE=$(tmux list-panes -F "#{pane_id} #{pane_title}" 2>/dev/null | grep -E "editor|render" | head -1 | awk '{print $1}')
    [[ -z "$EDITOR_PANE" ]] && EDITOR_PANE="%1"
fi

# Check current mode
CURRENT_MODE=$(cat "$MODE_FILE" 2>/dev/null || echo "editor")

if [[ "$CURRENT_MODE" == "render" ]]; then
    # In render mode - just update last_path
    :
else
    # In editor mode - open in nvim
    if [[ -S "$NVIM_PIPE" ]]; then
        # Nvim is running - send file via RPC
        "$NEXUS_EDITOR" --server "$NVIM_PIPE" --remote "$ABS_FILE"
    else
        # Start editor with the file
        if [[ "$NEXUS_EDITOR" == *"nvim"* ]]; then
            tmux respawn-pane -k -t "$EDITOR_PANE" "$WRAPPER '$NEXUS_EDITOR' --listen '$NVIM_PIPE' '$ABS_FILE'"
            
            # Wait for socket to be ready (robustness)
            for i in {1..20}; do
                [[ -S "$NVIM_PIPE" ]] && break
                sleep 0.1
            done
        else
            tmux respawn-pane -k -t "$EDITOR_PANE" "$WRAPPER '$NEXUS_EDITOR' '$ABS_FILE'"
        fi
        tmux select-pane -t "$EDITOR_PANE" -T "editor"
        echo "editor" > "$MODE_FILE"
    fi
    
    # Focus editor pane
    tmux select-window -t "$SESSION_NAME:workspace" 2>/dev/null || true
    tmux select-pane -t "$EDITOR_PANE"
fi
