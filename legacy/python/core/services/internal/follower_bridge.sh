# core/services/internal/follower_bridge.sh
# Event-driven listener that tells the editor to "ghost" Agent Zero.
# Uses action layer for all editor operations.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

echo "[*] Ghosting Bridge Active. Subscribing to AI_EVENT..."

# Subscribe to AI_EVENT on the bus
nxs-event subscribe AI_EVENT | while read -r event; do
    # Extract action and path from the event data
    ACTION=$(echo "$event" | jq -r '.data.action // empty')
    RAW_PATH=$(echo "$event" | jq -r '.data.path // empty')

    if [[ "$ACTION" == "ghost_open" && -n "$RAW_PATH" ]]; then
        # --- Remote-to-Local Path Translation ---
        LOCAL_PATH="$RAW_PATH"
        if [[ "$RAW_PATH" == /a0/* ]]; then
            REL_PATH="${RAW_PATH#/a0/}"
            LOCAL_PATH="$PROJECT_ROOT/$REL_PATH"
        fi

        if [[ -f "$LOCAL_PATH" ]]; then
            echo "[*] Syncing editor to: $LOCAL_PATH"
            # Open file via action layer (handles editor RPC + pane focus)
            "$PY" "$DISPATCH" editor.open "$LOCAL_PATH"
        else
            echo "[!] Warning: Path not found on host: $LOCAL_PATH"
        fi
    fi
done
