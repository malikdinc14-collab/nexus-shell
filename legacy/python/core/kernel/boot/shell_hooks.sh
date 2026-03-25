#!/bin/sh
# --- Nexus Shell Hooks (POSIX-Compliant) ---
# This file provides core aliases and functions for all supported shells (bash, zsh, sh).
# It should be sourced by shell-specific hook files or directly in ~/.bashrc / ~/.zshrc.

export NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
export NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"

# Ensure state directory exists
mkdir -p "$NEXUS_STATE"

# === edit/view Commands ===
# These work inside Nexus sessions to open files in the editor/render pane
alias edit="$NEXUS_ENGINE/lib/open.sh edit"
alias view="$NEXUS_ENGINE/lib/open.sh view"

# === Parallax Integration (Silent/Optional) ===
if [ -n "$NEXUS_PROJECT" ] && [ -f "$HOME/.parallax/bin/px-link" ]; then
    . "$HOME/.parallax/bin/px-link" 2>/dev/null
fi

# === Directory Sync ===
# Tracks current directory for cross-pane awareness
_nexus_sync_dir() {
    if [ -n "$NEXUS_PROJECT" ]; then
        pwd > "$NEXUS_STATE/last_dir"
    fi
}

# Shell-specific hook initialization
if [ -n "$ZSH_VERSION" ]; then
    # Zsh: use add-zsh-hook
    autoload -Uz add-zsh-hook 2>/dev/null
    add-zsh-hook chpwd _nexus_sync_dir 2>/dev/null
elif [ -n "$BASH_VERSION" ]; then
    # Bash: use PROMPT_COMMAND
    case "$PROMPT_COMMAND" in
        *_nexus_sync_dir*) ;;
        *) PROMPT_COMMAND="_nexus_sync_dir${PROMPT_COMMAND:+; $PROMPT_COMMAND}" ;;
    esac
fi

# Initial sync
_nexus_sync_dir

# === Tmux Helper ===
# Use 'tm' for nexus-aware tmux commands inside a session
if [ -n "$NEXUS_PROJECT" ]; then
    alias tm="tmux -f '$NEXUS_HOME/config/tmux/nexus.conf'"
fi

# === Quick Launchers ===
alias nxs="$NEXUS_HOME/bin/nxs"
alias nexus="$NEXUS_HOME/bin/nxs"

# === Kernel API ===
# state <key> [val] - Simple wrapper for the Station Manager
state() {
    if [ -z "$NEXUS_PROJECT" ]; then
        echo "Error: NEXUS_PROJECT not set. Are you inside a station?" >&2
        return 1
    fi
    if [ $# -eq 1 ]; then
        "$NEXUS_ENGINE/api/station_manager.sh" "$NEXUS_PROJECT" get "$1"
    else
        "$NEXUS_ENGINE/api/station_manager.sh" "$NEXUS_PROJECT" set "$1" "$2"
    fi
}
