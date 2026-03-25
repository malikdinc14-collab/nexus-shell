#!/bin/bash
# --- Nexus Open: edit/view Command Handler ---
# Layer 1 entry point. Delegates to action layer for editor operations.

ACTION="$1"
FILE="$2"

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

if [[ -z "$FILE" ]]; then
    echo "Usage: $ACTION <file>" >&2
    exit 1
fi

case "$ACTION" in
    "edit")
        exec "$PY" "$DISPATCH" editor.open "$FILE"
        ;;
    "view")
        # View mode — for now delegate to editor, can be extended later
        exec "$PY" "$DISPATCH" editor.open "$FILE"
        ;;
    *)
        echo "Unknown action: $ACTION. Usage: edit <file> | view <file>" >&2
        exit 1
        ;;
esac
