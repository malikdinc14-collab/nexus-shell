#!/usr/bin/env bash
# core/workspace/workspace_manager.sh
# Handles loading and orchestration of multi-root projects.

NEXUS_STATE_DIR="$HOME/.nexus"
mkdir -p "$NEXUS_STATE_DIR"

load_workspace() {
    local config_file="$1"
    if [[ ! -f "$config_file" ]]; then
        echo "[!] Error: Workspace file not found: $config_file"
        return 1
    fi

    echo "[*] Loading Workspace: $(jq -r '.name' "$config_file")"

    # Extract roots into a colon-separated string for Tmux and environment
    local roots=$(jq -r '.roots | join(":")' "$config_file")
    export NEXUS_ROOTS="$roots"
    export NEXUS_WORKSPACE_NAME=$(jq -r '.name' "$config_file")

    # Propagate to Tmux
    tmux set-environment -g NEXUS_ROOTS "$roots"
    tmux set-environment -g NEXUS_WORKSPACE_NAME "$NEXUS_WORKSPACE_NAME"

    echo "[*] Workspace Loaded. Aggregate search enabled for: $roots"
}

# Add nxs-workspace file detection for auto-loading
auto_load_workspace() {
    if [[ -f "./.nxs-workspace" ]]; then
        load_workspace "./.nxs-workspace"
    fi
}

case "$1" in
    load) load_workspace "$2" ;;
    auto) auto_load_workspace ;;
    *) echo "Usage: $0 {load <path>|auto}" ;;
esac
