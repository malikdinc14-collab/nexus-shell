#!/usr/bin/env bash
# core/hud/modules/gap.sh
# HUD Provider for the Gated Agent Protocol.

# 1. Get JSON from GAP engine
# Assuming gap is in PATH or alias
GAP_CMD="python3 /Users/Shared/Projects/Gated\ Agent\ Protocol/src/gap/main.py"
status_json=$($GAP_CMD shell status 2>/dev/null)

if [[ -n "$status_json" ]]; then
    progress=$(echo "$status_json" | jq -r '.progress')
    active_step=$(echo "$status_json" | jq -r '.active_step')
    
    # Format for HUD
    # Label: "Step 2.1 (45%)"
    label="Step $active_step ($progress%)"
    
    # Determine Color
    color="ORANGE"
    if [[ "$active_step" == "DONE" ]]; then color="GREEN"; fi
    
    # Output HUD JSON
    echo "{\"label\": \"$label\", \"color\": \"$color\"}"
else
    # Only output if there is an active mission
    exit 0
fi
