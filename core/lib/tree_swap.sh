#!/bin/bash

# --- Nexus Tree/Git Swap ---
# Toggles the tree pane between File Navigator (Yazi) and Git UI (LazyGit)

NEXUS_CONFIG="${NEXUS_CONFIG:-$HOME/.config/nexus-shell}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
NEXUS_SCRIPTS="$NEXUS_CONFIG/scripts"

# Load tools config
TOOLS_CONF="$NEXUS_CONFIG/tools.conf"
[[ -f "$TOOLS_CONF" ]] && source "$TOOLS_CONF"

# Tool defaults
NEXUS_FILES="${NEXUS_FILES:-yazi}"
NEXUS_GIT="${NEXUS_GIT:-lazygit}"

MODE_FILE="$NEXUS_STATE/tree_mode"
WRAPPER="$NEXUS_SCRIPTS/pane_wrapper.sh"

# Find the tree pane
TREE_PANE="${PX_NEXUS_TREE_PANE:-0}"

# Get current mode (default: files)
get_mode() {
    if [[ -f "$MODE_FILE" ]]; then
        cat "$MODE_FILE"
    else
        echo "files"
    fi
}

set_mode() {
    echo "$1" > "$MODE_FILE"
}

CURRENT_MODE=$(get_mode)

case "$CURRENT_MODE" in
    "files")
        # Switch to Git Mode
        set_mode "git"
        tmux respawn-pane -k -t "$TREE_PANE" "$WRAPPER $NEXUS_GIT"
        tmux select-pane -t "$TREE_PANE" -T "git"
        tmux display-message "Mode: GIT (lazygit)"
        ;;
        
    "git")
        # Switch back to Files
        set_mode "files"
        tmux respawn-pane -k -t "$TREE_PANE" "$WRAPPER $NEXUS_FILES"
        tmux select-pane -t "$TREE_PANE" -T "tree"
        tmux display-message "Mode: FILES (yazi)"
        ;;
esac
