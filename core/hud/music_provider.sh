#!/usr/bin/env bash
# core/hud/music_provider.sh
# Mocks music telemetry for the HUD (BPM, Tracking, CPU)

TELEMETRY_FILE="/tmp/nexus_telemetry.json"

while true; do
    # Mocking BPM and active channel
    bpm=$(( ( RANDOM % 20 ) + 120 ))
    channel=$(( ( RANDOM % 16 ) + 1 ))
    
    # Inject into global telemetry as custom fields
    local tmp_dir="/tmp/nexus_$(whoami)/tmp"
    mkdir -p "$tmp_dir"
    local temp_file=$(mktemp "$tmp_dir/music.XXXXXX")
    jq ".env.bpm = \"$bpm\" | .env.midi_ch = \"$channel\"" "$TELEMETRY_FILE" > "$temp_file" && mv "$temp_file" "$TELEMETRY_FILE"
    
    sleep 3
done
