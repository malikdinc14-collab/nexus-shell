#!/usr/bin/env bash
# core/hud/renderer.sh
# Renders the 1-line HUD strip using ANSI colors.

TELEMETRY_FILE="/tmp/nexus_telemetry.json"

# Color tokens (to be integrated with nxs-theme later)
BLUE='\033[0;34m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'

while true; do
    if [ -f "$TELEMETRY_FILE" ]; then
        # Read values
        ascent_lv=$(jq -r '.env.level // empty' "$TELEMETRY_FILE")
        branch=$(jq -r '.env.git_branch' "$TELEMETRY_FILE")

        # Select status icon/color
        case $agent_status in
            "thinking") status_color=$BLUE; icon="🧠" ;;
            "executing") status_color=$ORANGE; icon="⚙️" ;;
            "blocked") status_color=$RED; icon="🚨" ;;
            *) status_color=$GREEN; icon="👁️" ;;
        esac

        # Render 1-liner
        clear
        if [[ "$agent_status" == "blocked" ]]; then
            printf "${RED}${icon} ATTENTION:${NC} ${agent_mission} | ${CYAN}Branch:${NC} ${branch}\n"
        else
            # Check for supplemental telemetry
            custom_info=""
            if [[ -n "$ascent_lv" && "$ascent_lv" != "null" ]]; then
                custom_info="| ${CYAN}Level:${NC} ${ascent_lv} "
            fi
            
            printf "${status_color}${icon} ${agent_status}${NC} | ${CYAN}Workspace:${NC} ${workspace} ${custom_info}| ${CYAN}Profile:${NC} ${profile} | ${CYAN}Node:${NC} ${locality}\n"
        fi
    fi
    sleep 0.5
done
