#!/usr/bin/env bash
# pane-kill.sh — Kill focused pane (Alt+q)
# Shelves all tabs in the pane's stack, then kills the tmux pane.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export PYTHONPATH="$NEXUS_HOME/core:${PYTHONPATH:-}"
export PATH="$NEXUS_HOME/bin:$PATH"

NEXUS_CTL="python3 -m engine.cli.nexus_ctl"

# Shelve tabs in nexus state before destroying the pane
$NEXUS_CTL pane kill 2>/dev/null || true

# Actually kill the tmux pane
tmux kill-pane 2>/dev/null || true
