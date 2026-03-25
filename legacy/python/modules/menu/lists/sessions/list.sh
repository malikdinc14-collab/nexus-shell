#!/bin/bash
# modules/menu/lists/sessions/list.sh
# Pulse Provider for active sessions — uses adapter layer.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3

"$PY" -c "
import sys, os, json
sys.path.insert(0, os.path.join('$NEXUS_HOME', 'core'))
try:
    from engine.actions.resolver import AdapterResolver
    mux = AdapterResolver.multiplexer()
    raw = mux._run(['list-sessions', '-F', '#{session_name}'])
    if not raw:
        sys.exit(0)
    for session in raw.splitlines():
        if not session:
            continue
        windows = mux._run(['list-windows', '-t', session, '-F', '#{window_name}'])
        win_count = len(windows.splitlines()) if windows else 0
        label = f'{session} ({win_count} w)'
        print(json.dumps({
            'label': label,
            'type': 'ACTION',
            'payload': f'tmux attach -t {session}',
            'description': f'Session: {session}',
            'icon': 'terminal'
        }))
except Exception as e:
    print(json.dumps({'label': f'Error: {e}', 'type': 'DISABLED', 'payload': 'NONE'}))
" 2>/dev/null
