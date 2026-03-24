#!/bin/bash
# guard.sh - Handle safe exit and shutdown of Nexus session
# Recursively walks the process tree of every pane to kill ALL descendants.

LOG="/tmp/nexus_guard_debug.log"
echo "[$(date +%H:%M:%S)] guard.sh ENTRY args=[$*] NEXUS_HOME=[$NEXUS_HOME]" >> "$LOG"

log() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }

ACTION="$1"

# Resolve tmux command with socket isolation
TMUX_CMD="tmux"
if [[ -n "$SOCKET_LABEL" ]]; then
    TMUX_CMD="tmux -L $SOCKET_LABEL"
elif [[ "$SESSION_ID" == nexus_* ]]; then
    # Fallback: derive socket label from session if we have it
    TMUX_CMD="tmux -L ${SESSION_ID%_client_*}"
fi

# Resolve session ID.
# CRITICAL: We must resolve the MASTER session, even if we are in a client session.
SESSION_ID=$($TMUX_CMD display-message -p '#S' 2>/dev/null)
if [[ -n "$SESSION_ID" ]]; then
    # Strip client suffix if present (e.g. nexus_foo_client_123 -> nexus_foo)
    MASTER_SESSION="${SESSION_ID%_client_*}"
    log "Contextual Session: $SESSION_ID -> Master: $MASTER_SESSION"
    SESSION_ID="$MASTER_SESSION"
else
    # No client — find nexus sessions by name pattern
    # We try both default and labeled sockets if we know any
    SESSION_ID=$($TMUX_CMD list-sessions -F '#S' 2>/dev/null | grep '^nexus_' | head -1)
    log "No client context. Resolved session via list-sessions: $SESSION_ID"
fi

if [[ -z "$SESSION_ID" ]]; then
    log "WARNING: Could not determine session ID. Exiting."
    exit 1
fi

PROJECT_NAME="${SESSION_ID#nexus_}"

# Recursively collect all descendant PIDs of a given PID
get_descendants() {
    local pid=$1
    local children
    children=$(pgrep -P "$pid" 2>/dev/null)
    for child in $children; do
        echo "$child"
        get_descendants "$child"
    done
}

kill_pids() {
    local pane_pids="$1"
    
    if [[ -z "$pane_pids" ]]; then
        log "WARNING: No pane PIDs found."
        return
    fi

    # 2. Collect ALL descendant PIDs across all panes
    local all_pids=""
    for pid in $pane_pids; do
        local descendants
        descendants=$(get_descendants "$pid")
        all_pids="$all_pids $pid $descendants"
    done

    log "All PIDs to kill: $all_pids"

    # 3. SIGTERM everything (deepest children first = reverse order)
    for pid in $(echo "$all_pids" | tr ' ' '\n' | tac); do
        log "  SIGTERM $pid ($(ps -o comm= -p "$pid" 2>/dev/null))"
        kill -TERM "$pid" 2>/dev/null
    done

    # 4. Grace period
    sleep 0.5

    # 5. SIGKILL survivors
    for pid in $(echo "$all_pids" | tr ' ' '\n' | tac); do
        if kill -0 "$pid" 2>/dev/null; then
            log "  SIGKILL $pid (still alive)"
            kill -9 "$pid" 2>/dev/null
        fi
    done
}

kill_session_tree() {
    log "=== guard.sh session exit [$SESSION_ID] ==="
    
    # 1. Kill background services via station manager
    log "Cleaning up station: $PROJECT_NAME"
    "$NEXUS_HOME/core/engine/api/station_manager.sh" "$PROJECT_NAME" cleanup >> "$LOG" 2>&1

    # 2. Collect ALL PIDs from ALL windows in this master session
    local pane_pids
    pane_pids=$($TMUX_CMD list-panes -s -t "$SESSION_ID" -F '#{pane_pid}' 2>/dev/null)
    kill_pids "$pane_pids"
    
    # 3. Destroy the master session (kills all client sessions automatically)
    log "Killing master tmux session $SESSION_ID"
    $TMUX_CMD kill-session -t "$SESSION_ID" 2>/dev/null || true
    
    # 4. Kill the daemon so it restarts fresh next boot
    log "Stopping daemon..."
    pkill -f "daemon.py" 2>/dev/null || true

    # 5. Final stale pipe cleanup
    rm -f "/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe" 2>/dev/null

    log "=== guard.sh session complete ==="
}

kill_window_tree() {
    log "=== guard.sh window exit ==="
    local win_id
    win_id=$($TMUX_CMD display-message -p '#{window_id}' 2>/dev/null)
    
    if [[ -z "$win_id" ]]; then
        log "No active window id found, defaulting to session kill"
        kill_session_tree
        return
    fi
    
    local pane_pids
    pane_pids=$($TMUX_CMD list-panes -t "$win_id" -F '#{pane_pid}' 2>/dev/null)
    kill_pids "$pane_pids"
    
    log "Killing tmux window $win_id"
    $TMUX_CMD kill-window -t "$win_id" 2>/dev/null || true
    log "=== guard.sh window complete ==="
}

case "$ACTION" in
    exit_window|force_window)
        kill_window_tree
        ;;
    exit_session|force_session|exit|force)
        kill_session_tree
        ;;
    *)
        log "Unknown action: $ACTION"
        exit 1
        ;;
esac
