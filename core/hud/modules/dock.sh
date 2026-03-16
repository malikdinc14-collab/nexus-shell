#!/bin/bash
# core/hud/modules/dock.sh
# Detects minimized panes and reports to HUD.

# Search for any pane with @nexus_minimized == 1
MINIMIZED_COUNT=$(tmux list-panes -a -F '#{@nexus_minimized}' | grep -cx '1' | tr -d ' ')

if [[ "$MINIMIZED_COUNT" -gt 0 ]]; then
    # Get distinct roles of minimized panes
    ROLES=$(tmux list-panes -a -F '#{@nexus_minimized}|#{@nexus_role}|#{pane_id}' | grep '^1|' | cut -d'|' -f2 | sort | uniq | xargs | tr ' ' ',')
    # Use role if available, fallback to id
    [[ -z "$ROLES" || "$ROLES" == "null" ]] && ROLES="pane"
    
    echo "{\"label\": \"📥 [$ROLES]\", \"color\": \"ORANGE\"}"
else
    # Output empty to hide from HUD
    echo ""
fi
