#!/bin/bash
# lib/yazi_open.sh
# Bridge between Yazi and Nexus Shell to open files in the Editor pane.
#
# This is a Layer 1 (thin entry point) script. All logic lives in the
# action layer (Layer 2). No direct tmux/nvim calls here.

FILE_PATH="$1"
[[ -z "$FILE_PATH" ]] && exit 0

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"

# Resolve Python
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" \
|| PY="${Python_BIN:-python3}"

# Delegate to action layer — it handles path resolution, editor RPC,
# and pane focus through adapters.
exec "$PY" "$NEXUS_HOME/core/engine/actions/dispatch.py" editor.open "$FILE_PATH"
