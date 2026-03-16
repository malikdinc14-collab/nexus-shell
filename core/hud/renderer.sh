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
PURPLE='\033[0;35m'
DIM='\033[2m'
NC='\033[0m'

while true; do
        # 1. Core State
        workspace=$(jq -r '.env.workspace' "$TELEMETRY_FILE")
        profile=$(jq -r '.env.profile' "$TELEMETRY_FILE")
        locality=$(jq -r '.env.locality' "$TELEMETRY_FILE")
        branch=$(jq -r '.env.git_branch' "$TELEMETRY_FILE")

        # 2. Render Modules Dynamically
        module_info=""
        # Loop over each key in the .modules object
        while read -r mod_name; do
            if [[ -n "$mod_name" && "$mod_name" != "null" ]]; then
                # Get the 'label' or 'status' field from the module data
                label=$(jq -r ".modules[\"$mod_name\"].label // empty" "$TELEMETRY_FILE")
                color_name=$(jq -r ".modules[\"$mod_name\"].color // \"CYAN\"" "$TELEMETRY_FILE")
                
                case $color_name in
                    "ORANGE") mod_color=$ORANGE ;;
                    "GREEN") mod_color=$GREEN ;;
                    "BLUE") mod_color=$BLUE ;;
                    "RED") mod_color=$RED ;;
                    *) mod_color=$CYAN ;;
                esac

                if [[ -n "$label" ]]; then
                    module_info="${module_info}| ${mod_color}${mod_name^^}:${NC} ${label} "
                fi
            fi
        done < <(jq -r '.modules | keys[]' "$TELEMETRY_FILE" 2>/dev/null)

        # 3. Final Print
        # Use simple escape sequence to home cursor instead of full clear to prevent flicker
        printf "\033[H"
        
        # Calculate Sovereign Status
        sov_indicator="${DIM}idle${NC}"
        if [[ "$module_info" == *"BURN"* ]]; then
            sov_indicator="${PURPLE}⚡ active${NC}"
        fi

        printf "${GREEN}👁️ ${sov_indicator}${NC} | ${CYAN}WS:${NC} ${workspace} ${module_info}| ${CYAN}PF:${NC} ${profile} | ${CYAN}LOC:${NC} ${locality}\033[K"
    sleep 0.2
done
