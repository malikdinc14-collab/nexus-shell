#!/usr/bin/env bash
# core/commands/hud.sh
# Toggles or manages the HUD visibility within the session.

toggle_hud() {
    # Check if HUD window exists in Tmux
    if tmux list-windows | grep -q "HUD"; then
        # If it's visible, hide it (or vice versa)
        # For now, we'll just focus it
        tmux select-window -t HUD
    else
        # Provision it
        tmux new-window -n HUD -d "./core/hud/renderer.sh"
    fi
}

case "$1" in
    toggle) toggle_hud ;;
    *) echo "Usage: :hud toggle" ;;
esac
