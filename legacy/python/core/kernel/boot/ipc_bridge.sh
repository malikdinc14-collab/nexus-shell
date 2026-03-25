#!/bin/bash
# ipc_bridge.sh - Platform-Agnostic Focus & Identity Reporter
# V1: OSC-based signalling for standalone windows.

# This script is intended to be sourced in the user's shell profile (e.g. .zshrc)
# or called via precmd hooks to keep the Daemon informed of focus/state.

nxs_report_focus() {
    local CONTAINER_ID="${NEXUS_CONTAINER_ID:-$PPID}"
    # Send an OSC sequence that identifying this terminal to the Daemon
    # \033]666;focus;CONTAINER_ID\007
    # Note: This requires a terminal emulator that supports custom OSCs or 
    # a background listener that intercepts these.
    
    # Fallback: Direct IPC call to Daemon
    if [[ -S "/tmp/nexus_$(whoami).sock" ]]; then
        # Use a lightweight JSON blob
        echo "{\"action\": \"report_focus\", \"payload\": {\"container_id\": \"$CONTAINER_ID\"}}" | nc -U "/tmp/nexus_$(whoami).sock" >/dev/null 2>&1
    fi
}

# Auto-provision identity if missing
if [[ -z "$NEXUS_CONTAINER_ID" ]]; then
    export NEXUS_CONTAINER_ID="window_$(uuidgen | cut -d- -f1)"
fi
