#!/bin/bash
# unload_brains.sh - Shut down all local model backends

set -e

echo "🛑 Shutting down local intelligence backends..."

# 1. Kill Letta
PID_LETTA=$(lsof -ti :8083 2>/dev/null || true)
[[ -n "$PID_LETTA" ]] && kill "$PID_LETTA" && echo "  - Letta stopped."

# 2. Kill MLX Servers (Ports 8080-8085)
for PORT in {8080..8085}; do
    PID=$(lsof -ti :$PORT 2>/dev/null || true)
    if [[ -n "$PID" ]]; then
        kill "$PID"
        echo "  - Backend on Port $PORT stopped."
    fi
done

# 3. Kill Ollama
if command -v ollama >/dev/null 2>&1; then
    # On macOS, Ollama is usually an app, but let's try to stop the engine
    pkill -f "ollama serve" || true
    echo "  - Ollama engine stopped."
fi

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
"$PY" "$NEXUS_HOME/core/engine/actions/dispatch.py" pane.display-message "All local brains unloaded." 2>/dev/null
