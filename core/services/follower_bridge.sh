# core/services/follower_bridge.sh
# Event-driven listener that tells Neovim to "ghost" Agent Zero.

NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}${NEXUS_WINDOW_SUFFIX}.pipe"

echo "[*] Ghosting Bridge Active. Subscribing to AI_EVENT..."

# Subscribe to AI_EVENT on the bus
nxs-event subscribe AI_EVENT | while read -r event; do
    # Extract action and path from the event data
    ACTION=$(echo "$event" | jq -r '.data.action // empty')
    RAW_PATH=$(echo "$event" | jq -r '.data.path // empty')
    
    if [[ "$ACTION" == "ghost_open" && -n "$RAW_PATH" ]]; then
        # --- Remote-to-Local Path Translation ---
        # Agent Zero usually uses /a0/ as its internal project root.
        LOCAL_PATH="$RAW_PATH"
        if [[ "$RAW_PATH" == /a0/* ]]; then
            REL_PATH="${RAW_PATH#/a0/}"
            LOCAL_PATH="$PROJECT_ROOT/$REL_PATH"
        fi

        if [[ -f "$LOCAL_PATH" ]]; then
            echo "[*] Syncing Neovim to: $LOCAL_PATH"
            # Remote-send the edit command to the active nvim pipe
            nvim --server "$NVIM_PIPE" --remote-send ":e $LOCAL_PATH<CR>" 2>/dev/null
        else
            echo "[!] Warning: Slave path not found on host: $LOCAL_PATH"
        fi
    fi
done
