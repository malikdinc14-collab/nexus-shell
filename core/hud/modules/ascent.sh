#!/usr/bin/env bash
# core/hud/modules/ascent.sh
# Modular provider for Ascent Workspace telemetry.

ASCENT_STATE="/tmp/nexus_$(whoami)/ascent/progress.json"

if [[ -f "$ASCENT_STATE" ]]; then
    ascent_level=$(jq -r ".level" "$ASCENT_STATE" 2>/dev/null || echo "1")
    echo "{\"label\": \"Level ${ascent_level}\", \"color\": \"ORANGE\"}"
else
    # Fallback to a default if in an Ascent orbit but no state yet
    if [[ "$NEXUS_PROFILE" == "ascent" || "$NEXUS_PROFILE" == "sovereign" ]]; then
         echo '{"label": "Level 1", "color": "ORANGE"}'
    fi
fi
