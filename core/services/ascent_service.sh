#!/usr/bin/env bash
# core/services/ascent_service.sh
# Manages the user's learning progress and experience (EXP)

NEXUS_STATE="/tmp/nexus_$(whoami)/ascent"
mkdir -p "$NEXUS_STATE"
STATE_FILE="$NEXUS_STATE/progress.json"

# Initialize state if missing
if [[ ! -f "$STATE_FILE" ]]; then
    echo '{"level": 1, "exp": 0, "total_xp": 0, "rank": "Novice"}' > "$STATE_FILE"
fi

get_val() { jq -r ".$1" "$STATE_FILE"; }

update_xp() {
    local add_xp=$1
    local current_xp=$(get_val "exp")
    local total_xp=$(get_val "total_xp")
    local current_lv=$(get_val "level")
    
    new_xp=$((current_xp + add_xp))
    new_total=$((total_xp + add_xp))
    
    # Level Up Logic (Simulated)
    if [[ $new_xp -ge 100 ]]; then
        new_xp=$((new_xp - 100))
        current_lv=$((current_lv + 1))
        case $current_lv in
            5) rank="Apprentice" ;;
            10) rank="Journeyman" ;;
            20) rank="Architect" ;;
            *) rank=$(get_val "rank") ;;
        esac
    fi
    
    # Save back to file
    jq ".exp = $new_xp | .total_xp = $new_total | .level = $current_lv | .rank = \"$rank\"" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
}

case "$1" in
    add) update_xp "$2" ;;
    get) cat "$STATE_FILE" ;;
    *) echo "Usage: $0 {add <xp>|get}" ;;
esac
