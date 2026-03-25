#!/usr/bin/env bash
# core/services/internal/ascent_stats.sh
# Renders the TUI for the Ascent Statistics pane

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Loop for real-time updates
while true; do
    clear
    STATS=$("$NEXUS_HOME/core/services/internal/ascent_service.sh" get)
    
    LV=$(echo "$STATS" | jq -r ".level")
    XP=$(echo "$STATS" | jq -r ".exp")
    RANK=$(echo "$STATS" | jq -r ".rank")
    TOTAL=$(echo "$STATS" | jq -r ".total_xp")
    
    echo -e "\033[1;36m🏆 ASCENT MASTERMIND\033[0m"
    echo -e "\033[1;30m--------------------------\033[0m"
    echo -e "RANK:  \033[1;33m$RANK\033[0m"
    echo -e "LEVEL: \033[1;32m$LV\033[0m"
    echo -e "XP:    \033[1;34m$XP / 100\033[0m"
    echo -e "TOTAL: \033[1;30m$TOTAL XP\033[0m"
    echo -e "\033[1;30m--------------------------\033[0m"
    
    # Simulated Task List
    echo ""
    echo -e "\033[1;35mCURRENT CHALLENGES:\033[0m"
    echo -e " [ ] Integrate conflict matrix (+20 XP)"
    echo -e " [ ] Fix launcher recursion (+15 XP)"
    echo -e " [x] Implement Alt-j Jump (+25 XP)"
    
    sleep 5
done
