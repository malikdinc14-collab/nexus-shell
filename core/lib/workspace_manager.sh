#!/usr/bin/env bash
# lib/workspace_manager.sh
# Manages the virtual symlink layer for the Sovereign IDE.

SESSION_ID="${SESSION_ID:-default}"
WS_ROOT="/tmp/nexus/workspaces/$SESSION_ID"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
PROJECT_NAME="${PROJECT_NAME:-$(basename "$PROJECT_ROOT")}"

setup_workspace() {
    local MANIFEST="$1"
    echo "[*] Provisioning Sovereign Workspace: $SESSION_ID"
    
    # 1. Create sandbox
    mkdir -p "$WS_ROOT"
    
    # 2. Cleanup old links
    rm -rf "$WS_ROOT"/*
    
    if [[ -f "$MANIFEST" ]]; then
        echo "    [*] Processing Multi-Root Manifest: $(basename "$MANIFEST")"
        # Extract roots using python to handle JSON robustly
        python3 -c "
import json, os, subprocess
with open('$MANIFEST') as f:
    data = json.load(f)
    roots = data.get('roots', {})
    for name, path in roots.items():
        abs_path = os.path.abspath(os.path.expanduser(path))
        target = os.path.join('$WS_ROOT', name)
        subprocess.run(['ln', '-sf', abs_path, target])
        print(f'    [+] Anchored: {name} -> {abs_path}')
"
    else
        # 3. Create canonical project link
        # This becomes the "Root" in Yazi's eyes.
        ABS_PROJECT_ROOT=$(cd "$PROJECT_ROOT" && pwd)
        ln -sf "$ABS_PROJECT_ROOT" "$WS_ROOT/$PROJECT_NAME"
        
        echo "    [+] Anchored: $PROJECT_NAME -> $ABS_PROJECT_ROOT"
    fi
}

get_virtual_root() {
    echo "$WS_ROOT"
}

get_workspace_roots() {
    local MANIFEST="$1"
    if [[ -f "$MANIFEST" ]]; then
        # NEW: Return roots separated by NEWLINES to handle spaces
        python3 -c "
import json, os
with open('$MANIFEST') as f:
    data = json.load(f)
    roots = data.get('roots', {})
    for p in roots.values():
        print(os.path.abspath(os.path.expanduser(p)))
"
    else
        echo "$(cd "$PROJECT_ROOT" && pwd)"
    fi
}

# If called directly, setup
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    setup_workspace
fi
