#!/bin/bash

# --- Nexus Emergency Breaker: ATOMIC PURGE ---
# Enforces the Negative Space by physically zeroing the system.

echo "[!] EMERGENCY PURGE INITIATED..."

# 1. Kill all TMUX servers
tmux kill-server 2>/dev/null || true
tmux -L nexus kill-server 2>/dev/null || true

# 2. Recursive Signal 9 Purge
# We kill by full command path to avoid hitting unrelated tools
pkill -9 -f "pane_wrapper.sh"
pkill -9 -f "launcher.sh"
pkill -9 -f "layout_engine.sh"
pkill -9 -f "nexus_monitor"
pkill -9 -f "px-link"
pkill -9 -f "sleep 3.0"
pkill -9 -f "opencode"
pkill -9 -f "render_daemon.sh"
pkill -9 -f "nexus_sync"

# 3. Clean up the state
rm -f /tmp/nexus_station.log
rm -rf /tmp/nexus_$(whoami)
rm -f /tmp/nexus_monitor.pid

echo "[*] Purge complete. System at Zero-State."
