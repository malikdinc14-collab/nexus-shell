#!/usr/bin/env bash
# stack-pop.sh — Close active tab (Alt+w)
# Pops the active tab. If it's the last tab, asks for confirmation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export PYTHONPATH="$NEXUS_HOME/core:${PYTHONPATH:-}"
export PATH="$NEXUS_HOME/bin:$PATH"

NEXUS_CTL="python3 -m engine.cli.nexus_ctl"

_has() { command -v "$1" &>/dev/null; }

RESULT="$($NEXUS_CTL stack pop 2>/dev/null)" || {
    echo "Error: $NEXUS_CTL stack pop failed" >&2
    exit 1
}

# Check if we got a last_tab warning
WARNING=""
if _has jq; then
    WARNING="$(echo "$RESULT" | jq -r '.warning // empty')"
else
    WARNING="$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
print(data.get('warning', ''))
" <<< "$RESULT")"
fi

if [[ "$WARNING" == "last_tab" ]]; then
    # Last tab — ask for confirmation via tmux
    tmux confirm-before -p "Close last tab in this pane? (y/n)" \
        "run-shell '$NEXUS_HOME/bin/ui/pane-kill.sh'"
fi
