#!/usr/bin/env bash
# core/services/hud_service.sh
# Manages the HUD background processes.

SERVICE_DIR="/tmp/nexus_services"
mkdir -p "$SERVICE_DIR"

start_hud() {
    echo "Starting Status HUD Services..."
    # Start aggregator in background
    ./core/hud/telemetry_aggregator.sh & echo $! > "$SERVICE_DIR/hud_aggregator.pid"
    
    # We don't start the renderer here because it needs a visible Tmux pane.
    # The session manager will handle the pane creation.
}

stop_hud() {
    echo "Stopping Status HUD Services..."
    if [ -f "$SERVICE_DIR/hud_aggregator.pid" ]; then
        kill $(cat "$SERVICE_DIR/hud_aggregator.pid") && rm "$SERVICE_DIR/hud_aggregator.pid"
    fi
}

case "$1" in
    start) start_hud ;;
    stop) stop_hud ;;
    *) echo "Usage: $0 {start|stop}" ;;
esac
