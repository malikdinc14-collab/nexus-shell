#!/bin/bash
# core/boot/debug_tail.sh
# --- Nexus Debug Monitor ---

echo -e "\033[1;35m🌌 Nexus Debug Monitor Active\033[0m"
echo -e "Tailing all service logs for project: \033[1;36m$PROJECT_NAME\033[0m"
echo "----------------------------------------------------"

LOG_DIR="/tmp/nexus_$(whoami)/$PROJECT_NAME"
echo "Log Directory: $LOG_DIR"

# Check if directory exists
if [[ ! -d "$LOG_DIR" ]]; then
    echo "[!] Log directory does not exist yet. Waiting..."
    for i in {1..20}; do
        [[ -d "$LOG_DIR" ]] && break
        sleep 0.5
    done
fi

# Multi-tail all log files
echo "[*] Starting live monitor..."
tail -f "$LOG_DIR"/*.log 2>/dev/null || echo "[!] No log files found in $LOG_DIR"

# Keep window open if tail fails
echo "--- Monitor Stopped ---"
/bin/zsh
