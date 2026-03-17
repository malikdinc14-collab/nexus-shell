#!/bin/bash
# core/services/internal/stream_monitor.sh
# Sandbox Stream Monitor for Nexus Shell (watches Agent Zero)

AGENT0_DIR="/Users/Shared/Projects/external_repos/agent0"
LOG_FILE="/tmp/agent0_sandbox_stream.log"

# Function to find the latest session log if we want to watch historicals
# get_latest_log() {
#     ls -t "$AGENT0_DIR/logs"/*.html 2>/dev/null | head -n 1
# }

clear
echo -e "\033[1;36m=== SANDBOX STREAM MONITOR ===\033[0m"
echo -e "\033[1;30mWatching: $LOG_FILE\033[0m"
echo "--------------------------------"

if [[ ! -f "$LOG_FILE" ]]; then
    touch "$LOG_FILE"
    echo "Waiting for Agent Zero output..." >> "$LOG_FILE"
fi

# We use tail with a small filter to clean up some ANSI if needed, 
# or just raw tail for maximum fidelity.
tail -f "$LOG_FILE"
