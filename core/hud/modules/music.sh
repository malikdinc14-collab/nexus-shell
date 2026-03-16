#!/usr/bin/env bash
# core/hud/modules/music.sh
# Modular provider for Music telemetry (Mocks BPM/Channel).

# Mocking BPM and active channel
bpm=$(( ( RANDOM % 20 ) + 120 ))
channel=$(( ( RANDOM % 16 ) + 1 ))

echo "{\"label\": \"${bpm}bpm Ch${channel}\", \"color\": \"BLUE\"}"
