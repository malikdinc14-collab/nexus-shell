#!/bin/bash
# core/hud/modules/mesh.sh
# HUD Module for Model-Server Mesh & Proxy Status

# Determine Status and Color
if nc -z localhost 4000 2>/dev/null; then
    PROXY_LABEL="MESH"
    PROXY_COLOR="GREEN"
else
    PROXY_LABEL="MESH"
    PROXY_COLOR="RED"
fi

if nc -z localhost 8080 2>/dev/null; then
    SRV_LABEL="SRV"
    SRV_COLOR="GREEN"
else
    SRV_LABEL="SRV"
    SRV_COLOR="RED"
fi

# Determine Output Mode
OUTPUT_JSON=false
# Fix: Use a more robust way to check for --json argument
# This handles cases where --json might be combined with other arguments or not the first argument.
for arg in "$@"; do
    if [[ "$arg" == "--json" ]]; then
        OUTPUT_JSON=true
        break # No need to check further if --json is found
    fi
done

# The aggregator expects a single label/color or we can return a combined label
if [[ "$OUTPUT_JSON" == "true" ]]; then
    # Fix: The JSON output should reflect the combined status, not just SRV_COLOR
    # If either SRV or PROXY is RED, the combined status should be RED.
    if [[ "$SRV_COLOR" == "RED" || "$PROXY_COLOR" == "RED" ]]; then
        echo "{\"label\": \"SRV MESH\", \"color\": \"RED\"}"
    else
        echo "{\"label\": \"SRV MESH\", \"color\": \"GREEN\"}"
    fi
else
    # Return Tmux-compatible string
    # We use the ● and ○ icons as before
    if [[ "$SRV_COLOR" == "GREEN" ]]; then SRV_ICON="#[fg=green]●#[fg=default]"; else SRV_ICON="#[fg=red]○#[fg=default]"; fi
    if [[ "$PROXY_COLOR" == "GREEN" ]]; then PROXY_ICON="#[fg=green]●#[fg=default]"; else PROXY_ICON="#[fg=red]○#[fg=default]"; fi
    echo "${SRV_ICON} SRV ${PROXY_ICON} MESH"
fi
