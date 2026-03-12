#!/usr/bin/env bash
# core/mosaic_engine.sh
# Orchestrates the "Mission Control" visual transformation.

ACTION="${1:-start}"

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/.." && pwd)}"
SESSION_ID=$(tmux display-message -p '#S' 2>/dev/null)
WINDOW_ID=$(tmux display-message -p '#I' 2>/dev/null)
PROJECT_ROOT=$(tmux display-message -p '#{pane_current_path}')

start_mosaic() {
    # 1. Capture current layout to restore later
    # We'll use the Nexus station_manager or just a temporary file
    # For now, let's assume we want to restore 'vscodelike' or the '__saved_session__'
    
    # 2. Generate the Mosaic JSON
    python3 "${NEXUS_HOME}/core/mosaic_generator.py"
    
    # 3. Clear the stage and switch
    nxs-switch-layout /tmp/nexus_mosaic.json
}

restore_layout() {
    # 1. Read selection
    local selection=$(cat /tmp/nexus_mosaic_selection 2>/dev/null)
    local type=$(echo "$selection" | cut -d: -f1)
    local id=$(echo "$selection" | cut -d: -f2)
    
    # 2. Restore original layout (Defaults to vscodelike for now)
    # TODO: Make this actually restore the PREVIOUS layout
    nxs-switch-layout vscodelike
    
    # 3. Wait for layout to build then apply selection
    sleep 0.5
    
    if [[ "$type" == "nvim" ]]; then
        local pipe="/tmp/nexus_$(whoami)/pipes/nvim_${NEXUS_PROJECT}.pipe"
        nvim --server "$pipe" --remote-send "<C-\><C-n>:${id}tabnext<CR>"
        tmux select-pane -t editor
    elif [[ "$type" == "shell" ]]; then
         # Swap the term tab back 
         # (This needs better integration with terminal_tabs.sh)
         tmux select-pane -t terminal
    fi
}

case "$ACTION" in
    start) start_mosaic ;;
    restore) restore_layout ;;
esac
