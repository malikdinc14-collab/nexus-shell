#!/bin/bash
# core/boot/debug_tail.sh
# --- Nexus Debug Monitor ---

echo -e "\033[1;35m🌌 Nexus Debug Monitor Active\033[0m"
echo -e "Tailing all service logs for project: \033[1;36m$PROJECT_NAME\033[0m"
echo "----------------------------------------------------"

LOG_DIR="/tmp/nexus_$(whoami)/$PROJECT_NAME"
mkdir -p "$LOG_DIR"

# Wait for logs to be created
sleep 1

# Using tail with --follow=name to handle file recreation
tail -f "$LOG_DIR"/*.log 2>/dev/null | grep --line-buffered -v "DEBUG" || echo "[!] No logs found yet..."

# Keep window open if tail fails
/bin/zsh
