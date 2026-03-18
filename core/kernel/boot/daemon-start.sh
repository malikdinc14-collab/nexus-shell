#!/bin/bash
# core/kernel/boot/daemon-start.sh
# Ensures the Sovereign Daemon is running for the current user.

USER_NAME=$(whoami)
SOCKET_PATH="/tmp/nexus_${USER_NAME}.sock"
DAEMON_PATH="${NEXUS_HOME}/core/services/internal/daemon.py"
LOG_DIR="/tmp/nexus_${USER_NAME}"
LOG_FILE="${LOG_DIR}/daemon.log"

mkdir -p "$LOG_DIR"

check_daemon() {
    if [[ -S "$SOCKET_PATH" ]]; then
        # Try a quick ping via python
        if python3 -c "import socket; s=socket.socket(socket.AF_UNIX); s.connect('$SOCKET_PATH'); s.send(b'{\"action\":\"ping\"}'); s.close()" 2>/dev/null; then
            return 0
        fi
        # Stale socket
        rm -f "$SOCKET_PATH"
    fi
    return 1
}

if ! check_daemon; then
    echo "[boot] Starting Sovereign Daemon..."
    # Start in background, redirected to log
    python3 "$DAEMON_PATH" > "$LOG_FILE" 2>&1 &
    
    # Wait for socket to appear
    for i in {1..20}; do
        if [[ -S "$SOCKET_PATH" ]]; then
            echo "[boot] Sovereign Daemon Ready."
            return 0
        fi
        sleep 0.1
    done
    echo "[core/kernel/boot/daemon-start.sh] [ERROR] Daemon failed to start."
    return 1
else
    # Already running
    return 0
fi
