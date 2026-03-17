#!/bin/bash
# core/services/internal/beacon_overlay.sh
# The "Sovereign Beacon" - A minimalist HUD pulse

ASCENT_DIR="/Users/Shared/Projects/school"
SOV_DIR="/Users/Shared/Projects/sovereign-inference"

while true; do
    # 1. Extract Ascent Progress
    if [[ -d "$ASCENT_DIR" ]]; then
        # Parsing a hypothetical status file or running a quick check
        # For demo, let's derive it from run count vs target
        DONE=$(ls "$ASCENT_DIR/runs" 2>/dev/null | wc -l)
        TOTAL=100 # Default target
        PROGRESS=$(( DONE * 100 / TOTAL ))
        ASCENT_STR="🎓 Ascent: ${PROGRESS}%"
    else
        ASCENT_STR="🎓 Ascent: N/A"
    fi

    # 2. Extract Model Health
    ACTIVE_MODEL=$(nxs-state get project.active_model 2>/dev/null)
    if [[ -n "$ACTIVE_MODEL" ]]; then
        IS_HOSTING=$(pgrep -f "sov host" > /dev/null && echo "Active" || echo "Idle")
        MODEL_STR="🌌 Model: ${ACTIVE_MODEL} ($IS_HOSTING)"
    else
        MODEL_STR="🌌 Model: None"
    fi

    # 3. Format Message
    MSG="${ASCENT_STR} | ${MODEL_STR}"

    # 4. Trigger Pulse (Top line message)
    # Using display-message for a non-intrusive pulse
    tmux display-message -d 3000 "$MSG"

    # 5. Wait for next pulse
    sleep 30
done
