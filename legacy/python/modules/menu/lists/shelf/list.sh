#!/bin/bash
# pillars/shelf/list.sh
# Pulse Provider for the Nexus Shelf (stowed panes)

script=$NEXUS_HOME/core/kernel/exec/shelf.sh

if [[ ! -x "$script" ]]; then
    printf '{"label": "Shelf Service Error", "type": "DISABLED", "payload": "NONE", "icon": "⚠️"}\n'
    exit 0
fi

# The shelf script already outputs JSON lines in the new protocol!
# We can just pipe it.
"$script" list
