#!/usr/bin/env zsh

# --- Nexus Shell Hooks ---
# Provides edit/view commands and shell integration
# Source this in your ~/.zshrc or ~/.nexus.zsh

export NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
export NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"

# Ensure state directory exists
mkdir -p "$NEXUS_STATE"

# === edit/view Commands ===
# These work inside Nexus sessions to open files in the editor/render pane

alias edit="$NEXUS_ENGINE/lib/open.sh edit"
alias view="$NEXUS_ENGINE/lib/open.sh view"

# === Parallax Integration ===
# Only auto-link inside Nexus sessions or if explicitly forced
if [[ -n "$NEXUS_PROJECT" || -n "$PX_FORCE_LINK" ]]; then
    if [[ -f "$HOME/.parallax/bin/px-link" ]]; then
        source "$HOME/.parallax/bin/px-link"
    fi
fi

# === Directory Sync ===
# Tracks current directory for cross-pane awareness

_nexus_sync_dir() {
    if [[ -n "$NEXUS_PROJECT" ]]; then
        echo "$(pwd)" > "$NEXUS_STATE/last_dir"
    fi
}

# Hook into directory changes
autoload -Uz add-zsh-hook
add-zsh-hook chpwd _nexus_sync_dir

# Initial sync
_nexus_sync_dir

# === Tmux Helper ===
# Use 'tm' for nexus-aware tmux commands inside a session

if [[ -n "$NEXUS_PROJECT" ]]; then
    alias tm="tmux -f '$NEXUS_HOME/config/tmux/nexus.conf'"
fi

# === Quick Launchers ===
# 'nxs' points to the public bin entry point
alias nxs="$NEXUS_HOME/bin/nxs"
alias nexus="$NEXUS_HOME/bin/nxs"

# === Kernel API ===
# state <key> [val] - Simple wrapper for the Station Manager
state() {
    if [[ -z "$NEXUS_PROJECT" ]]; then
        echo "Error: NEXUS_PROJECT not set. Are you inside a station?" >&2
        return 1
    fi
    if [[ $# -eq 1 ]]; then
        "$NEXUS_ENGINE/api/station_manager.sh" "$NEXUS_PROJECT" get "$1"
    else
        "$NEXUS_ENGINE/api/station_manager.sh" "$NEXUS_PROJECT" set "$1" "$2"
    fi
}
