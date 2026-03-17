#!/usr/bin/env bash
# core/ui/hud/ascent_provider.sh
# Extension for the Ascent Workspace to inject Level/XP into telemetry.

TELEMETRY_FILE="/tmp/nexus_telemetry.json"
ASCENT_STATE="/tmp/nexus_$(whoami)/ascent/progress.json"

while true; do
    if [[ -f "$ASCENT_STATE" ]]; then
        ascent_level=$(jq -r ".level" "$ASCENT_STATE" 2>/dev/null || echo "1")
        # Inject into global telemetry
        local tmp_dir="/tmp/nexus_$(whoami)/tmp"
        mkdir -p "$tmp_dir"
        local temp_file=$(mktemp "$tmp_dir/ascent.XXXXXX")
        jq ".env.level = \"$ascent_level\"" "$TELEMETRY_FILE" > "$temp_file" && mv "$temp_file" "$TELEMETRY_FILE"
    fi
    sleep 2
done
