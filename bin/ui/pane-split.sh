#!/usr/bin/env bash
# pane-split.sh — Split pane (Alt+v / Alt+s)
# Usage: pane-split.sh <v|h>
# Creates a tmux split and registers the new pane with the stack manager.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export PYTHONPATH="$NEXUS_HOME/core:${PYTHONPATH:-}"
export PATH="$NEXUS_HOME/bin:$PATH"

NEXUS_CTL="python3 -m engine.cli.nexus_ctl"

DIRECTION="${1:-v}"

# Validate direction
case "$DIRECTION" in
    v|h) ;;
    *)
        echo "Usage: pane-split.sh <v|h>" >&2
        exit 1
        ;;
esac

# Create the actual tmux split
tmux split-window -"$DIRECTION"

# Register the new pane with nexus stack manager
$NEXUS_CTL stack push 2>/dev/null || true
