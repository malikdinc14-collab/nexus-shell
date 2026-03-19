#!/usr/bin/env zsh
# core/kernel/exec/router.sh
# The Execution Router for Nexus.
# Intercepts the pure STDOUT of the Menu and routes it to the specific environment action.

# Read from STDIN if piped, otherwise take $1
if [[ -p /dev/stdin ]]; then
    read -r PAYLOAD
else
    PAYLOAD="$1"
fi

[[ -z "$PAYLOAD" ]] && exit 0

SCRIPT_DIR="${0:A:h}"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"
NEXUS_CTL="$NEXUS_HOME/bin/nexus-ctl"

# Delegate everything to nexus-ctl, which resolves and executes the plan
"$NEXUS_CTL" "$PAYLOAD" --execute
