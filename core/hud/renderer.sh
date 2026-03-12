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
        agent_status=$(jq -r '.agent.status' "$TELEMETRY_FILE")
        agent_mission=$(jq -r '.agent.mission' "$TELEMETRY_FILE" 2>/dev/null)
        workspace=$(jq -r '.env.workspace' "$TELEMETRY_FILE")
        profile=$(jq -r '.env.profile' "$TELEMETRY_FILE")
        locality=$(jq -r '.env.locality' "$TELEMETRY_FILE")
        ascent_lv=$(jq -r '.env.level // empty' "$TELEMETRY_FILE" 2>/dev/null)
        bpm=$(jq -r '.env.bpm // empty' "$TELEMETRY_FILE" 2>/dev/null)
        midi_ch=$(jq -r '.env.midi_ch // empty' "$TELEMETRY_FILE" 2>/dev/null)
        branch=$(jq -r '.env.git_branch // empty' "$TELEMETRY_FILE" 2>/dev/null)

        # Select status icon/color
        case $agent_status in
            "thinking") status_color=$BLUE; icon="🧠" ;;
            "executing") status_color=$ORANGE; icon="⚙️" ;;
            "blocked") status_color=$RED; icon="🚨" ;;
            "safety_blocked") status_color=$RED; icon="🛡️  BLOCK" ;;
            *) status_color=$GREEN; icon="👁️" ;;
        esac

        # Render 1-liner
        clear
        if [[ "$agent_status" == "blocked" ]]; then
            printf "${RED}${icon} ATTENTION:${NC} ${agent_mission} | ${CYAN}Branch:${NC} ${branch}\n"
        else
            # Check for supplemental telemetry
            custom_info=""
            if [[ -n "$ascent_lv" && "$ascent_lv" != "null" && "$ascent_lv" != "" ]]; then
                custom_info="| ${CYAN}Level:${NC} ${ascent_lv} "
            elif [[ -n "$bpm" && "$bpm" != "null" && "$bpm" != "" ]]; then
                custom_info="| ${CYAN}BPM:${NC} ${bpm} | ${CYAN}MIDI:${NC} ch${midi_ch} "
            fi
            
            # Check for GAP Mission
            mission_id=$(jq -r '.mission.id // empty' "$TELEMETRY_FILE" 2>/dev/null)
            mission_status=$(jq -r '.mission.status // empty' "$TELEMETRY_FILE" 2>/dev/null)
            mission_info=""
            if [[ -n "$mission_id" && "$mission_id" != "null" ]]; then
                mission_info="| ${ORANGE}MISSION:${NC} ${mission_id} [${mission_status}] "
            fi

            printf "${status_color}${icon} ${agent_status}${NC} | ${CYAN}Workspace:${NC} ${workspace} ${custom_info}${mission_info}| ${CYAN}Profile:${NC} ${profile} | ${CYAN}Node:${NC} ${locality}\n"
        fi
    fi
    sleep 0.5
done
