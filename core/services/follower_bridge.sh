#!/bin/bash
# core/services/follower_bridge.sh
# Background listener that tells Neovim to "ghost" Agent Zero.

LOG_FILE="/tmp/agent0_sandbox_stream.log"
NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}${NEXUS_WINDOW_SUFFIX}.pipe"

echo "[*] Ghosting Bridge Active. Monitoring $LOG_FILE..."

tail -f "$LOG_FILE" | while read -r line; do
    if [[ "$line" == *"[SIGNAL:OPEN]"* ]]; then
        RAW_PATH=$(echo "$line" | sed 's/.*>> //')
        
        # --- Remote-to-Local Path Translation ---
        # Agent Zero usually uses /a0/ as its internal project root.
        # We translate this back to the local PROJECT_ROOT.
        LOCAL_PATH="$RAW_PATH"
        if [[ "$RAW_PATH" == /a0/* ]]; then
            # Strip /a0/ and prepend project root
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
