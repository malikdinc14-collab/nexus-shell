#!/bin/bash

# --- Nexus Editor/Render Swap ---
# Toggles the editor pane between Editor (Nvim) and Render (Glow) mode

# Use NEXUS_CONFIG (set by launcher), fallback to standard path
NEXUS_CONFIG="${NEXUS_CONFIG:-$HOME/.config/nexus-shell}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
NEXUS_SCRIPTS="$NEXUS_CONFIG/scripts"

# Load tools config
TOOLS_CONF="$NEXUS_CONFIG/tools.conf"
[[ -f "$TOOLS_CONF" ]] && source "$TOOLS_CONF"

# Tool defaults
NEXUS_EDITOR="${NEXUS_EDITOR:-nvim}"
NEXUS_RENDER="${NEXUS_RENDER:-glow}"

SESSION_NAME=$(tmux display-message -p '#S')
PROJECT_NAME=${SESSION_NAME#nexus_}
NVIM_PIPE="${NEXUS_PIPE:-$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe}"
MODE_FILE="$NEXUS_STATE/editor_mode"
LAST_FILE="$NEXUS_STATE/last_path"

# Ensure state directory exists
mkdir -p "$NEXUS_STATE/pipes"

# Get current mode (default: editor)
get_mode() {
    if [[ -f "$MODE_FILE" ]]; then
        cat "$MODE_FILE"
    else
        echo "editor"
    fi
}

# Set mode
set_mode() {
    echo "$1" > "$MODE_FILE"
}

# Get current file from Nvim or state
get_current_file() {
    # Try to get from nvim via RPC
    if [[ -S "$NVIM_PIPE" ]] && command -v nvim &>/dev/null; then
        local file=$(nvim --server "$NVIM_PIPE" --remote-expr "expand('%:p')" 2>/dev/null)
        if [[ -n "$file" && "$file" != "" ]]; then
            echo "$file"
            return
        fi
    fi
    # Fallback to state file
    if [[ -f "$LAST_FILE" ]]; then
        cat "$LAST_FILE"
    fi
}

# Find the editor pane (pane 1 in standard layout, or pane with editor/render title)
get_editor_pane() {
    # Use exported index if available
    if [[ "${PX_NEXUS_EDITOR_PANE:- -1}" -ge 0 ]]; then
        echo "$PX_NEXUS_EDITOR_PANE"
        return
    fi
    # Try by title first
    local pane=$(tmux list-panes -F "#{pane_id} #{pane_title}" 2>/dev/null | grep -E "editor|render" | head -1 | awk '{print $1}')
    if [[ -n "$pane" ]]; then
        echo "$pane"
    else
        # Fallback to pane index 1 (second pane, after tree)
        echo "%1"
    fi
}

CURRENT_MODE=$(get_mode)
CURRENT_FILE=$(get_current_file)
EDITOR_PANE=$(get_editor_pane)
WRAPPER="$NEXUS_SCRIPTS/pane_wrapper.sh"

# Build editor command (only nvim supports --listen)
build_editor_cmd() {
    local file="${1:-.}"
    if [[ "$NEXUS_EDITOR" == *"nvim"* ]]; then
        echo "$NEXUS_EDITOR --listen '$NVIM_PIPE' '$file'"
    else
        echo "$NEXUS_EDITOR '$file'"
    fi
}

case "$CURRENT_MODE" in
    "editor")
        # Switch to Render Mode
        set_mode "render"
        
        # Save current file path for renderer
        if [[ -n "$CURRENT_FILE" ]]; then
            echo "$CURRENT_FILE" > "$LAST_FILE"
        fi
        
        tmux respawn-pane -k -t "$EDITOR_PANE" "$WRAPPER $NEXUS_SCRIPTS/render_daemon.sh"
        tmux select-pane -t "$EDITOR_PANE" -T "render"
        tmux display-message "Mode: RENDER"
        ;;
        
    "render")
        # Switch back to Editor
        set_mode "editor"
        
        SAVED_FILE=$(cat "$LAST_FILE" 2>/dev/null || echo ".")
        EDITOR_CMD=$(build_editor_cmd "$SAVED_FILE")
        tmux respawn-pane -k -t "$EDITOR_PANE" "$WRAPPER $EDITOR_CMD"
        tmux select-pane -t "$EDITOR_PANE" -T "editor"
        tmux display-message "Mode: EDITOR"
        ;;
esac
