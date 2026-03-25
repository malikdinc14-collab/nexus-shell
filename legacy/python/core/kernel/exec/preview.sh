#!/bin/bash
# core/kernel/exec/preview.sh
# Hotswaps from Editor to Renderer for the current file.
# Uses action layer for editor and stack operations.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

# Query editor for current file via action layer
FILE=$("$PY" "$DISPATCH" editor.current-file 2>/dev/null)

if [[ -n "$FILE" && -f "$FILE" ]]; then
    # Push to Local Stack (In-Place)
    "$NEXUS_HOME/core/kernel/stack/stack" push "local" "$NEXUS_HOME/core/ui/view/view '$FILE'" "Preview: $(basename "$FILE")"
fi
