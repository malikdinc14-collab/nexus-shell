#!/bin/bash
# core/boot/stop.sh
# Aggressive Nexus Cleanup Service

echo "[*] Initializing Nexus Termination Sequence..."

# 1. Kill Tmux Sessions
if command -v tmux &>/dev/null; then
    sessions=$(tmux list-sessions | grep "^nexus_" | cut -d: -f1)
    if [[ -n "$sessions" ]]; then
        echo "[*] Closing Nexus Tmux Sessions..."
        for s in $sessions; do
            tmux kill-session -t "$s" 2>/dev/null
        done
    fi
fi

# 2. Kill Background Services
echo "[*] Reaping Background Daemons..."
pkill -f "telemetry_aggregator.sh" 2>/dev/null
pkill -f "event_server.py" 2>/dev/null
pkill -f "sid.py" 2>/dev/null
pkill -f "follower_bridge.sh" 2>/dev/null

# 3. Cleanup state/pipes
echo "[*] Purging Ephemeral State..."
rm -rf /tmp/nexus_* 2>/dev/null
rm -f /tmp/nexus_telemetry.json 2>/dev/null

# 4. Final check for survivors
# This handles cases where scripts were renamed or processes are stuck
survivors=$(pgrep -f "nexus-shell")
if [[ -n "$survivors" ]]; then
    echo "[!] Warning: Force-killing persistent Nexus processes..."
    kill -9 $survivors 2>/dev/null
fi

echo "[*] Nexus Solidification Complete (System Stopped)."
