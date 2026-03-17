#!/bin/bash

# --- Nexus Open: edit/view Command Handler ---
# Redirects file opening to the appropriate pane (no prompts)

ACTION="$1"
FILE="$2"

NEXUS_CONFIG="${NEXUS_CONFIG:-$HOME/.config/nexus-shell}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
NEXUS_SCRIPTS="$NEXUS_CONFIG/scripts"

# Load tools config
TOOLS_CONF="$NEXUS_CONFIG/tools.conf"
[[ -f "$TOOLS_CONF" ]] && source "$TOOLS_CONF"

NEXUS_EDITOR="${NEXUS_EDITOR:-nvim}"

if [[ -z "$FILE" ]]; then
    echo "Usage: $ACTION <file>"
    exit 1
fi

# Resolve to absolute path
ABS_FILE=$(realpath "$FILE" 2>/dev/null || echo "$FILE")

if [[ ! -f "$ABS_FILE" ]]; then
    echo "File not found: $FILE"
    exit 1
fi

SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null)
PROJECT_NAME=${SESSION_NAME#nexus_}
NVIM_PIPE="${NEXUS_PIPE:-$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe}"
LAST_FILE="$NEXUS_STATE/last_path"
MODE_FILE="$NEXUS_STATE/editor_mode"
WRAPPER="$NEXUS_SCRIPTS/pane_wrapper.sh"

# Find the editor/render pane
if [[ "${PX_NEXUS_EDITOR_PANE:- -1}" -ge 0 ]]; then
    EDITOR_PANE="$PX_NEXUS_EDITOR_PANE"
else
    EDITOR_PANE=$(tmux list-panes -F "#{pane_id} #{pane_title}" 2>/dev/null | grep -E "editor|render" | head -1 | awk '{print $1}')
    [[ -z "$EDITOR_PANE" ]] && EDITOR_PANE="%1"
fi

# Update state
mkdir -p "$NEXUS_STATE/pipes"
echo "$ABS_FILE" > "$LAST_FILE"

case "$ACTION" in
    "edit")
        # Ensure we're in editor mode
        echo "editor" > "$MODE_FILE"
        
        if [[ -S "$NVIM_PIPE" ]]; then
            # Nvim is running - send file via RPC
            nvim --server "$NVIM_PIPE" --remote "$ABS_FILE"
        else
            # Start editor with the file
            if [[ "$NEXUS_EDITOR" == *"nvim"* ]]; then
                tmux respawn-pane -k -t "$EDITOR_PANE" "$WRAPPER $NEXUS_EDITOR --listen '$NVIM_PIPE' '$ABS_FILE'"
            else
                tmux respawn-pane -k -t "$EDITOR_PANE" "$WRAPPER $NEXUS_EDITOR '$ABS_FILE'"
            fi
            tmux select-pane -t "$EDITOR_PANE" -T "editor"
        fi
        tmux select-pane -t "$EDITOR_PANE"
        ;;
        
    "view")
        # Switch to render mode - the render daemon will pick up the file from last_path
        echo "render" > "$MODE_FILE"
        tmux respawn-pane -k -t "$EDITOR_PANE" "$WRAPPER $NEXUS_SCRIPTS/render_daemon.sh"
        tmux select-pane -t "$EDITOR_PANE" -T "render"
        tmux select-pane -t "$EDITOR_PANE"
        ;;
        
    *)
        echo "Unknown action: $ACTION"
        echo "Usage: edit <file> | view <file>"
        exit 1
        ;;
esac
