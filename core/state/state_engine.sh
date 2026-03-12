#!/bin/bash
# core/state/state_engine.sh
# The Unified State Engine for Nexus Shell.
# Provides a clean API for persistent IDE state.

STATE_FILE="${PROJECT_ROOT:-.}/.nexus/state.json"
mkdir -p "$(dirname "$STATE_FILE")"
[[ ! -f "$STATE_FILE" ]] && echo "{}" > "$STATE_FILE"

# Helper to execute python logic for JSON manipulation
_json_op() {
    python3 -c "
import json, os, sys

def get_nested(data, path):
    keys = path.split('.')
    for k in keys:
        if isinstance(data, dict):
            data = data.get(k, {})
        else:
            return None
    return data

def set_nested(data, path, value):
    keys = path.split('.')
    curr = data
    for k in keys[:-1]:
        if k not in curr or not isinstance(curr[k], dict):
            curr[k] = {}
        curr = curr[k]
    curr[keys[-1]] = value

# Load
try:
    with open('$STATE_FILE', 'r') as f:
        state = json.load(f)
except:
    state = {}

action = sys.argv[1]
path = sys.argv[2]

if action == 'get':
    res = get_nested(state, path)
    if isinstance(res, (dict, list)):
        print(json.dumps(res))
    else:
        print(res if res is not None else '')

elif action == 'set':
    val = sys.argv[3]
    # Try to parse as JSON if it looks like it
    try:
        if val.startswith('{') or val.startswith('['):
            val = json.loads(val)
    except:
        pass
    set_nested(state, path, val)
    with open('$STATE_FILE', 'w') as f:
        json.dump(state, f, indent=4)

elif action == 'delete':
    keys = path.split('.')
    curr = state
    for k in keys[:-1]:
        curr = curr.get(k, {})
    if keys[-1] in curr:
        del curr[keys[-1]]
    with open('$STATE_FILE', 'w') as f:
        json.dump(state, f, indent=4)
" "$@"
}

case "$1" in
    get)    _json_op get "$2" ;;
    set)    _json_op set "$2" "$3" ;;
    delete) _json_op delete "$2" ;;
    push)   # TODO: Sync to cloud/remote if needed
            echo "Push not implemented" ;;
    *)      echo "Usage: nxs-state [get|set|delete] <path> [value]" ;;
esac
