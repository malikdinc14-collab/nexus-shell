#!/bin/bash
# core/boot/boot_loader.sh
# Infrastructure for automatic execution of "boot" list items.

ACTION="$1" # start | stop
PROJECT_NAME="${NEXUS_PROJECT}"
NEXUS_STATE_DIR="/tmp/nexus_$(whoami)/$PROJECT_NAME"
PID_FILE="$NEXUS_STATE_DIR/boot_services.pids"
LOG_FILE="$NEXUS_STATE_DIR/boot.log"

[[ -z "$PROJECT_NAME" ]] && { echo "Error: NEXUS_PROJECT not set."; exit 1; }

mkdir -p "$NEXUS_STATE_DIR"

log() { echo "[$(date +%T)] [Boot] $*" >> "$LOG_FILE"; }

case "$ACTION" in
    start)
        log "Starting boot sequence..."
        # 1. Discover boot items using the menu engine
        # We use the CLI engine directly to avoid TUI hangs.
        BOOT_ITEMS=$(python3 "$NEXUS_HOME/modules/menu/lib/core/menu_engine.py" --context boot 2>/dev/null)
        
        if [[ -z "$BOOT_ITEMS" || "$BOOT_ITEMS" == *"Empty:"* ]]; then
            log "No boot items found."
            exit 0
        fi

        # 2. Iterate and execute
        echo "$BOOT_ITEMS" | while read -r item_json; do
            # Extract payload (the script/command to run)
            # We assume it's a valid ACTION type with a payload
            PAYLOAD=$(echo "$item_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('payload', ''))" 2>/dev/null)
            LABEL=$(echo "$item_json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('label', ''))" 2>/dev/null)
            
            if [[ -n "$PAYLOAD" && "$PAYLOAD" != "NONE" ]]; then
                log "Booting: $LABEL ($PAYLOAD)"
                # Execute in background, send output to log
                (eval "$PAYLOAD" >> "$LOG_FILE" 2>&1) &
                echo "$!" >> "$PID_FILE"
            fi
        done
        ;;

    stop)
        if [[ ! -f "$PID_FILE" ]]; then
            exit 0
        fi

        log "Stopping boot services..."
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                log "Stopping service PID $pid..."
                kill -TERM "$pid" 2>/dev/null
            fi
        done < "$PID_FILE"

        # Grace period for shutdown
        sleep 1

        # Force kill survivors
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                log "Force killing service PID $pid..."
                kill -KILL "$pid" 2>/dev/null
            fi
        done < "$PID_FILE"

        rm -f "$PID_FILE"
        log "Boot services stopped."
        ;;

    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac
