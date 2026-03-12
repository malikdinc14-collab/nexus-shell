#!/usr/bin/env bash
# core/hud/renderer.sh
# Renders the 1-line HUD strip using ANSI colors.

TELEMETRY_FILE="/tmp/nexus_telemetry.json"

# Color tokens (to be integrated with nxs-theme later)
BLUE='\033[0;34m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

while true; do
    if [ -f "$TELEMETRY_FILE" ]; then
        # Read values
        agent_status=$(jq -r '.agent.status' "$TELEMETRY_FILE")
        workspace=$(jq -r '.env.workspace' "$TELEMETRY_FILE")
        profile=$(jq -r '.env.profile' "$TELEMETRY_FILE")
        locality=$(jq -r '.env.locality' "$TELEMETRY_FILE")
        ascent_lv=$(jq -r '.env.level' "$TELEMETRY_FILE")

        # Select status icon/color
        case $agent_status in
            "thinking") status_color=$BLUE; icon="🧠" ;;
            "executing") status_color=$ORANGE; icon="⚙️" ;;
            *) status_color=$GREEN; icon="👁️" ;;
        esac

        # Render 1-liner
        clear
        printf "${status_color}${icon} ${agent_status}${NC} | ${CYAN}Workspace:${NC} ${workspace} | ${CYAN}Level:${NC} ${ascent_lv} | ${CYAN}Profile:${NC} ${profile} | ${CYAN}Node:${NC} ${locality}\n"
    fi
    sleep 0.5
done
