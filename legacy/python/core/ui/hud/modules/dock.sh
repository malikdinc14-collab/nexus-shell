#!/bin/bash
# core/ui/hud/modules/dock.sh
# HUD Module: Detects minimized panes and reports to HUD.
# Uses action layer for pane queries.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3

# Query minimized panes via Python action layer
"$PY" -c "
import sys, os
sys.path.insert(0, os.path.join('$NEXUS_HOME', 'core'))
try:
    from engine.actions.resolver import AdapterResolver
    mux = AdapterResolver.multiplexer()
    raw = mux._run(['list-panes', '-a', '-F', '#{@nexus_minimized}|#{@nexus_role}|#{pane_id}'])
    if not raw:
        sys.exit(0)
    minimized = [l for l in raw.splitlines() if l.startswith('1|')]
    if minimized:
        roles = set(l.split('|')[1] for l in minimized if l.split('|')[1] and l.split('|')[1] != 'null')
        label = ','.join(sorted(roles)) if roles else 'pane'
        print('{\"label\": \"📥 [' + label + ']\", \"color\": \"ORANGE\"}')
except Exception:
    pass
" 2>/dev/null
