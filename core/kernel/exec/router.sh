#!/usr/bin/env zsh
# core/kernel/exec/router.sh
# The Execution Router for Nexus
# Intercepts the pure STDOUT of the Menu and routes it to the specific environment action.

# Read from STDIN if piped, otherwise take $1
if [[ -p /dev/stdin ]]; then
    read -r PAYLOAD
else
    PAYLOAD="$1"
fi

# Bootstrap Paths
SCRIPT_DIR="${0:A:h}"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"

# If no payload, do nothing
if [[ -z "$PAYLOAD" ]]; then
    exit 0
fi

# Split the payload on the first pipe
TYPE="${PAYLOAD%%|*}"
DATA="${PAYLOAD#*|}"

# Helper to find a pane by its exact title
get_pane_by_title() {
    local target_title="$1"
    tmux list-panes -F "#{pane_id} #{pane_title}" | grep -E " $target_title$" | head -n 1 | awk '{print $1}'
}

# Find commonly used panes
EDITOR_PANE=$(get_pane_by_title "editor")
TERM_PANE=$(get_pane_by_title "terminal")

# Determine Execution Context
# If NXS_STRICT_LOCAL is set, we never jump.
STRICT_LOCAL="${NXS_STRICT_LOCAL:-false}"

# V3 Unified Intelligence Kernel Delegation
# ---
# Convert legacy TYPE|DATA into a Kernel Plan
PLAN_JSON=$(python3 "$NEXUS_HOME/core/engine/api/intent_resolver.py" "$TYPE|$DATA" 2>/dev/null)

if [[ -z "$PLAN_JSON" ]]; then
    echo "Kernel Error: Could not resolve payload $TYPE|$DATA"
    exit 1
fi

STRATEGY=$(echo "$PLAN_JSON" | jq -r '.strategy')
TARGET_ROLE=$(echo "$PLAN_JSON" | jq -r '.role')
CMD=$(echo "$PLAN_JSON" | jq -r '.cmd')
IDENTITY=$(echo "$PLAN_JSON" | jq -r '.name // empty')

case "$STRATEGY" in
    stack_switch)
        IDX=$(echo "$PLAN_JSON" | jq -r '.index')
        "$NEXUS_HOME/core/kernel/stack/nxs-stack" switch "local" "$IDX"
        ;;
    stack_replace)
        "$NEXUS_HOME/core/kernel/stack/nxs-stack" replace "$TARGET_ROLE" "$CMD" "$IDENTITY"
        ;;
    stack_push)
        "$NEXUS_HOME/core/kernel/stack/nxs-stack" push "$TARGET_ROLE" "$CMD" "$IDENTITY"
        ;;
    exec_local)
        eval "$CMD"
        ;;
    remote_control)
        TARGET=$(echo "$PLAN_JSON" | jq -r '.target')
        "$NEXUS_HOME/core/kernel/bin/nxs-control" "$TARGET" "$CMD"
        ;;
    *)
        # Default fallback for router is usually just executing the command in the target slot
        "$NEXUS_HOME/core/kernel/stack/nxs-stack" push "$TARGET_ROLE" "$CMD" "$IDENTITY"
        ;;
esac
