#!/usr/bin/env bash
# core/mosaic_engine.sh
# Orchestrates the "Mission Control" visual transformation.

ACTION="${1:-start}"

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
SESSION_ID=$(tmux display-message -p '#S' 2>/dev/null)
WINDOW_ID=$(tmux display-message -p '#I' 2>/dev/null)
PROJECT_ROOT=$(tmux display-message -p '#{pane_current_path}')

start_mosaic() {
    # 1. Capture current layout to restore later
    local last_comp=$(tmux show-window-options -v @nexus_last_composition 2>/dev/null)
    [[ -z "$last_comp" ]] || [[ "$last_comp" == "/tmp/nexus_mosaic.json" ]] && last_comp="vscodelike"
    echo "$last_comp" > /tmp/nexus_mosaic_prev
    
    # 2. Generate the Mosaic JSON
    python3 "${NEXUS_KERNEL}/layout/mosaic_generator.py"
    
    # 3. Switch to the dynamic composition
    "${NEXUS_BOOT}/dispatch.sh" ":composition /tmp/nexus_mosaic.json"
}

restore_layout() {
    # 1. Read selection and previous state
    local selection=$(cat /tmp/nexus_mosaic_selection 2>/dev/null)
    local prev_comp=$(cat /tmp/nexus_mosaic_prev 2>/dev/null)
    [[ -z "$prev_comp" ]] && prev_comp="vscodelike"
    
    local type=$(echo "$selection" | cut -d: -f1)
    local id=$(echo "$selection" | cut -d: -f2)
    
    # 2. Restore original layout
    "${NEXUS_BOOT}/dispatch.sh" ":composition $prev_comp"
    
    # 3. Wait for layout to build then apply selection
    sleep 0.8
    
    if [[ "$type" == "nvim"* ]]; then
        local pipe="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe"
        if [[ "$type" == "nvim" ]]; then
            # Switch Tab
            nvim --server "$pipe" --remote-send "<C-\><C-n>:${id}tabnext<CR>"
        else
            # Switch Buffer
            nvim --server "$pipe" --remote-send "<C-\><C-n>:buffer ${id}<CR>"
        fi
        tmux select-pane -t editor
    fi
}

case "$ACTION" in
    start) start_mosaic ;;
    restore) restore_layout ;;
esac
