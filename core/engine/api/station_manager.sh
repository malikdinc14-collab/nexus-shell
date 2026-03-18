#!/bin/bash
# core/engine/api/station_manager.sh - Zero-Dependency State Store
# Centralizes project context across multiple Terminal Windows.

NEXUS_STATE_ROOT="/tmp/nexus_$(whoami)"

# Usage: nexus-state <project> get <key>
# Usage: nexus-state <project> set <key> <value>
# Usage: nexus-state <project> init

cmd_init() {
    local project="$1"
    local pdir="$NEXUS_STATE_ROOT/$project"
    mkdir -p "$pdir/pipes"
    [[ ! -f "$pdir/state.json" ]] && echo "{}" > "$pdir/state.json"
    
    # Start event bus if not already running
    local bus_pid_file="$pdir/bus.pid"
    if [[ ! -f "$bus_pid_file" ]] || ! kill -0 $(cat "$bus_pid_file" 2>/dev/null) 2>/dev/null; then
        # Find nexus core directory
        local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        local nexus_engine="$(cd "$script_dir/.." && pwd)"
        
        # Start event bus in background
        NEXUS_PROJECT="$project" python3 "$nexus_engine/bus/event_server.py" > "$pdir/bus.log" 2>&1 &
        echo $! > "$bus_pid_file"
        
        # Wait for socket to be created
        local socket="$pdir/bus.sock"
        local timeout=5
        while [[ ! -S "$socket" ]] && [[ $timeout -gt 0 ]]; do
            sleep 0.2
            ((timeout--))
        done
        
        if [[ -S "$socket" ]]; then
            echo "[Station] Event bus started (pid: $(cat "$bus_pid_file"))" >&2
        else
            echo "[Station] Warning: Event bus failed to start" >&2
        fi
    fi
    
    echo "$pdir"
}

cmd_get() {
    local project="$1"
    local key="$2"
    local state_file="$NEXUS_STATE_ROOT/$project/state.json"
    
    if [[ ! -f "$state_file" ]]; then
        return 1
    fi
    
    # Use python for JSON parsing to avoid jq dependency in core kernel
    python3 -c "
import json, sys
try:
    with open('$state_file', 'r') as f:
        data = json.load(f)
        print(data.get('$key', ''))
except:
    sys.exit(1)
"
}

cmd_set() {
    local project="$1"
    local key="$2"
    local val="$3"
    local state_file="$NEXUS_STATE_ROOT/$project/state.json"
    
    python3 -c "
import json, sys
try:
    try:
        with open('$state_file', 'r') as f:
            data = json.load(f)
    except:
        data = {}
    
    data['$key'] = '$val'
    with open('$state_file', 'w') as f:
        json.dump(data, f)
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)
"
}

cmd_cleanup() {
    local project="$1"
    local pdir="$NEXUS_STATE_ROOT/$project"
    
    # Stop event bus
    local bus_pid_file="$pdir/bus.pid"
    if [[ -f "$bus_pid_file" ]]; then
        local pid=$(cat "$bus_pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "[Station] Stopping event bus (pid: $pid)" >&2
            kill "$pid" 2>/dev/null
            sleep 0.5
            # Force kill if still running
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$bus_pid_file"
    fi
    
    # Remove socket
    rm -f "$pdir/bus.sock"
    
    echo "[Station] Cleanup complete" >&2
}

# --- Router ---
PROJECT="$1"
ACTION="$2"
shift 2

case "$ACTION" in
    init) cmd_init "$PROJECT" ;;
    get)  cmd_get  "$PROJECT" "$@" ;;
    set)  cmd_set  "$PROJECT" "$@" ;;
    cleanup) cmd_cleanup "$PROJECT" ;;
    *)    echo "Usage: $0 <project> [init|get|set|cleanup] ..." >&2; exit 1 ;;
esac
