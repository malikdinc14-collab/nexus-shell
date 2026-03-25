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
