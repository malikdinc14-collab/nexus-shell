#!/usr/bin/env bash
# Nexus Shell - Daemon Manager
# Orchestrates background services in a hidden Tmux window natively via SpecDD.

set -e

# Ensure we are inside a Nexus session
if [ -z "$NEXUS_SESSION" ]; then
    echo "Error: NEXUS_SESSION is not set. Are you running inside Nexus Shell?" >&2
    exit 1
fi

DAEMON_WINDOW="[services]"

function ensure_daemon_window() {
    # Create the window silently if it doesn't already exist
    if ! tmux has-session -t "${NEXUS_SESSION}:${DAEMON_WINDOW}" 2>/dev/null; then
        tmux new-window -d -t "${NEXUS_SESSION}" -n "${DAEMON_WINDOW}"
    fi
}

function start_daemon() {
    local service_id="$1"
    shift
    local cmd="$@"

    if [ -z "$service_id" ] || [ -z "$cmd" ]; then
        echo "Usage: daemon_manager start <service_id> <command...>" >&2
        return 1
    fi

    ensure_daemon_window

    # Check if a pane with this title already exists globally in the dedicated window
    local existing_pane=$(tmux list-panes -t "${NEXUS_SESSION}:${DAEMON_WINDOW}" -F "#{pane_title}:#{pane_id}" | awk -F: -v id="${service_id}" '$1 == id {print $2}')
    
    if [ -n "$existing_pane" ]; then
        echo "Error: Service '${service_id}' is already running in pane ${existing_pane}." >&2
        return 1
    fi

    # Split a new detached pane returning its ID
    local new_pane=$(tmux split-window -d -P -F "#{pane_id}" -t "${NEXUS_SESSION}:${DAEMON_WINDOW}")
    
    # Set the precise title for process bookkeeping
    tmux select-pane -T "${service_id}" -t "${new_pane}"
    
    # Dispatch the raw command to the isolated pane
    tmux send-keys -t "${new_pane}" "${cmd}" C-m
    
    echo "Started service '${service_id}' seamlessly in hidden dimension ${NEXUS_SESSION}:${DAEMON_WINDOW}."
}

function stop_daemon() {
    local service_id="$1"
    
    if [ -z "$service_id" ]; then
        echo "Usage: daemon_manager stop <service_id>" >&2
        return 1
    fi

    if ! tmux has-session -t "${NEXUS_SESSION}:${DAEMON_WINDOW}" 2>/dev/null; then
        echo "No services running."
        return 0
    fi

    local existing_pane=$(tmux list-panes -t "${NEXUS_SESSION}:${DAEMON_WINDOW}" -F "#{pane_title}:#{pane_id}" | awk -F: -v id="${service_id}" '$1 == id {print $2}')
    
    if [ -z "$existing_pane" ]; then
        echo "Service '${service_id}' is not currently running." >&2
        return 1
    fi

    # Gracefully send interrupt, then aggressively kill pane to prevent zombie loops
    tmux send-keys -t "${existing_pane}" C-c
    sleep 1
    tmux kill-pane -t "${existing_pane}"
    
    echo "Terminated service '${service_id}'."
}

function list_daemons() {
    if ! tmux has-session -t "${NEXUS_SESSION}:${DAEMON_WINDOW}" 2>/dev/null; then
        echo "No daemon services currently running."
        return 0
    fi
    
    echo "Active Daemons in Session ${NEXUS_SESSION}:"
    # List panes, ignoring the default nameless placeholder pane 
    tmux list-panes -t "${NEXUS_SESSION}:${DAEMON_WINDOW}" -F "  - #{pane_title} [ID: #{pane_id}]" | awk '!/  -  \[ID/'
}

cmd="$1"
shift

case "$cmd" in
    start)
        start_daemon "$@"
        ;;
    stop)
        stop_daemon "$@"
        ;;
    list)
        list_daemons
        ;;
    *)
        echo "Usage: $0 {start|stop|list} ..." >&2
        exit 1
        ;;
esac
