#!/usr/bin/env bash
# core/kernel/boot/first_run.sh
# First-Run Wizard for Nexus Shell
# Detects installed tools and helps user configure their environment

set -e

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
NEXUS_CORE="$NEXUS_HOME/core"
PROFILE_DIR="$HOME/.nexus"
PROFILE_FILE="$PROFILE_DIR/profile.yaml"
FIRST_RUN_FLAG="$PROFILE_DIR/.first_run_complete"

# Colors
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
DIM='\033[2m'
NC='\033[0m'

# Source detector
source "$NEXUS_HOME/core/engine/lib/detector.sh"

show_banner() {
    clear
    echo -e "${CYAN}"
    cat << 'EOF'
    _   _  _______  __  _  _  _____
   | \ | ||  ____ ||  || | ||  ___|
   |  \| || |__    |  || | || |___ 
   | .   ||  __|   |  || | ||___  |
   | |\  || |____  \  \/  /  ___| |
   |_| \_||_______| \____/  |_____|
EOF
    echo -e "${NC}"
    echo -e "${WHITE}    First-Run Setup Wizard${NC}"
    echo -e "${DIM}    ------------------------------------------${NC}"
    echo ""
}

phase_header() {
    local phase="$1"
    local title="$2"
    echo ""
    echo -e "${CYAN}━━━ PHASE $phase: $title ━━━${NC}"
    echo ""
}

# Initialize profile directory
init_profile_dir() {
    mkdir -p "$PROFILE_DIR"
}

# Detect installed tools and save to profile
detect_and_save() {
    phase_header "1" "SYSTEM SCAN"
    echo -e "${DIM}Scanning for installed tools...${NC}"
    sleep 1
    
    # Run detection
    local detected_json=$(detect_as_json)
    
    # Parse and display
    local roles=$(echo "$detected_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for role, tool in data.get('roles', {}).items():
    print(f'  ✓ {role}: {tool}')
for role in ['editor', 'explorer', 'chat', 'terminal', 'viewer', 'search']:
    if role not in data.get('roles', {}):
        print(f'  ○ {role}: not found')
")
    
    echo -e "${WHITE}Detected Tools:${NC}"
    echo "$roles"
    
    # Save to profile
    echo "$detected_json" | python3 -c "
import json, sys, yaml
from datetime import datetime

data = json.load(sys.stdin)
profile = {
    'version': 1,
    'created': datetime.now().isoformat(),
    'last_modified': datetime.now().isoformat(),
    'detected': data.get('tools', {}),
    'roles_detected': data.get('roles', {}),
    'roles': {r: (t[0] if isinstance(t, list) else t) for r, t in data.get('roles', {}).items()},
    'extensions': [],
    'preferences': {
        'first_run_complete': False
    }
}

with open('$PROFILE_FILE', 'w') as f:
    yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
"
    
    echo ""
    echo -e "${GREEN}✓ Detection saved to $PROFILE_FILE${NC}"
}

# Interactive role selection
select_roles() {
    phase_header "2" "ROLE ASSIGNMENT"
    echo -e "${DIM}Assign tools to specific system roles.${NC}"
    echo -e "${DIM}Choose a number from the list, or enter a custom name.${NC}"
    echo ""
    
    local roles=("editor" "explorer" "chat" "terminal" "viewer" "search")
    
    get_role_default() {
        case "$1" in
            editor) echo "nvim" ;;
            explorer) echo "yazi" ;;
            chat) echo "opencode" ;;
            terminal) echo "zsh" ;;
            viewer) echo "glow" ;;
            search) echo "grepai" ;;
        esac
    }
    
    get_role_desc() {
        case "$1" in
            editor) echo "Code/text editing" ;;
            explorer) echo "File navigation" ;;
            chat) echo "AI pair programming" ;;
            terminal) echo "Inner Environment (e.g. zsh, bash, or multiplexer like zellij)" ;;
            viewer) echo "Content viewing" ;;
            search) echo "Code search" ;;
        esac
    }
    
    for role in "${roles[@]}"; do
        local desc=$(get_role_desc "$role")
        local default_tool=$(get_role_default "$role")
        
        # Load detected candidates + current choice
        local candidates=$(python3 -c "
import yaml
try:
    with open('$PROFILE_FILE') as f:
        data = yaml.safe_load(f)
    roles_map = data.get('roles_detected', data.get('roles', {}))
    current = data.get('roles', {}).get('$role', '')
    
    # Filter candidates by role
    detected_for_role = roles_map.get('$role', [])
    if isinstance(detected_for_role, str): detected_for_role = [detected_for_role]
    
    options = []
    if current: options.append(f'{current} (current)')
    
    # Priority for Terminal
    if '$role' == 'terminal':
        for sh in ['zsh', 'bash', 'sh']:
            if sh != current: options.append(f'{sh} (raw shell)')
            
    if default_tool := '$default_tool':
        if default_tool != current and f'{default_tool} (raw shell)' not in options:
            options.append(f'{default_tool} (default)')
            
    for name in detected_for_role:
        if name not in [current, '$default_tool']:
            options.append(name)
            
    print('\n'.join(options))
except: pass
")

        echo -e "${WHITE}Role: $role${NC}"
        echo -e "${DIM}Description: $desc${NC}"
        
        local options_arr=()
        local count=0
        while IFS= read -r line; do
            [[ -n "$line" ]] || continue
            count=$((count + 1))
            options_arr+=("$line")
            echo -e "  $count) $line"
        done <<< "$candidates"
        
        echo -e "  m) Manual entry..."
        echo ""
        
        local choice=""
        local chosen_tool=""
        
        while [[ -z "$chosen_tool" ]]; do
            echo -ne "${CYAN}Select [1-$count, or m]: ${NC}"
            read -r choice
            
            if [[ "$choice" == "m" ]]; then
                echo -ne "Enter custom tool name for $role: "
                read -r chosen_tool
            elif [[ "$choice" =~ ^[0-9]+$ ]] && [[ "$choice" -le "$count" ]] && [[ "$choice" -gt 0 ]]; then
                # Extract clean name (remove (current) or (default) suffix)
                chosen_tool=$(echo "${options_arr[$((choice-1))]}" | sed 's/ (.*)//')
            elif [[ -z "$choice" ]]; then
                # Default to first option (usually current or default)
                chosen_tool=$(echo "${options_arr[0]}" | sed 's/ (.*)//')
            else
                echo -e "${YELLOW}Invalid selection.${NC}"
            fi
        done
        
        # Save to profile
        python3 -c "
import yaml
with open('$PROFILE_FILE') as f:
    data = yaml.safe_load(f)
data['roles']['$role'] = '$chosen_tool'
with open('$PROFILE_FILE', 'w') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
"
        echo -e "${GREEN}✓ $role set to: $chosen_tool${NC}"
        echo ""
    done
    
    echo -e "${GREEN}✓ All role assignments saved${NC}"
}

# Suggest and install missing extensions
suggest_extensions() {
    phase_header "3" "EXTENSION SUGGESTIONS"
    
    # Get suggestions
    local suggestions=$(suggest_missing_extensions)
    
    if [[ -z "$suggestions" ]]; then
        echo -e "${GREEN}✓ All core roles are configured!${NC}"
        echo ""
        return
    fi
    
    echo -e "${DIM}Recommended extensions for missing roles:${NC}"
    echo ""
    
    # Format for fzf
    local fzf_input=""
    while IFS='|' read -r name role desc; do
        [[ -n "$name" ]] || continue
        fzf_input+="$name ($role) - $desc"$'\n'
    done <<< "$suggestions"
    
    if [[ -n "$fzf_input" ]]; then
        echo "$fzf_input" | fzf --multi \
            --header="Select extensions to install (Tab to select, Enter to confirm)" \
            --prompt="Install > " \
            --height=40% \
            --border=rounded > /tmp/nxs_selected_extensions
        
        if [[ -s /tmp/nxs_selected_extensions ]]; then
            echo ""
            echo -e "${WHITE}Installing selected extensions...${NC}"
            
            while read -r selection; do
                local name=$(echo "$selection" | cut -d' ' -f1)
                echo -e "${DIM}  Installing $name...${NC}"
                "$NEXUS_HOME/extensions/loader.sh" install "$name" 2>/dev/null || \
                    echo -e "${YELLOW}  ⚠ Could not install $name automatically${NC}"
            done < /tmp/nxs_selected_extensions
            
            rm -f /tmp/nxs_selected_extensions
        fi
    fi
    
    echo ""
}

# Optional: browse all extensions
browse_extensions() {
    phase_header "4" "OPTIONAL EXTENSIONS"
    
    echo -e "${DIM}Browse additional extensions? (y/N): ${NC}"
    read -r browse
    
    if [[ "$browse" =~ ^[Yy]$ ]]; then
        # List all extensions by category
        local ext_list=$("$NEXUS_HOME/extensions/loader.sh" list-all 2>/dev/null || list_all_extensions)
        
        echo "$ext_list" | fzf --multi \
            --header="Select additional extensions to install" \
            --prompt="Install > " \
            --height=60% \
            --border=rounded > /tmp/nxs_optional_extensions
        
        if [[ -s /tmp/nxs_optional_extensions ]]; then
            echo ""
            while read -r selection; do
                local name=$(echo "$selection" | cut -d' ' -f1)
                echo -e "${DIM}  Installing $name...${NC}"
                "$NEXUS_HOME/extensions/loader.sh" install "$name" 2>/dev/null || \
                    echo -e "${YELLOW}  ⚠ Could not install $name${NC}"
            done < /tmp/nxs_optional_extensions
            
            rm -f /tmp/nxs_optional_extensions
        fi
    fi
}

# List all extensions (helper)
list_all_extensions() {
    for manifest in $(get_all_manifests); do
        local name=$(parse_manifest "$manifest" "name")
        local category=$(parse_manifest "$manifest" "category")
        local desc=$(parse_manifest "$manifest" "description")
        local binary=$(parse_manifest "$manifest" "binary")
        
        local installed="○"
        [[ -n "$binary" ]] && detect_binary "$binary" && installed="✓"
        
        echo "$installed $name [$category] - $desc"
    done | sort
}

# Finalize and save profile
finalize() {
    phase_header "5" "COMPLETE"
    
    # Mark first run complete
    python3 -c "
import yaml
from datetime import datetime
with open('$PROFILE_FILE') as f:
    data = yaml.safe_load(f)
data['preferences']['first_run_complete'] = True
data['last_modified'] = datetime.now().isoformat()
with open('$PROFILE_FILE', 'w') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
"
    
    # Create flag file
    touch "$FIRST_RUN_FLAG"
    
    # Display final configuration
    echo -e "${WHITE}Your Configuration:${NC}"
    echo ""
    python3 -c "
import yaml
with open('$PROFILE_FILE') as f:
    data = yaml.safe_load(f)
for role, tool in data.get('roles', {}).items():
    print(f'  {role}: {tool}')
"
    
    echo ""
    echo -e "${GREEN}✅ Setup complete!${NC}"
    echo ""
    echo -e "${DIM}Your profile is saved at: $PROFILE_FILE${NC}"
    echo -e "${DIM}Edit anytime with: nxs profile edit${NC}"
    echo ""
    echo -e "${WHITE}Run 'nxs boot' to start your station.${NC}"
    echo ""
}

# Main wizard flow
main() {
    # Check if already completed
    if [[ -f "$FIRST_RUN_FLAG" ]] && [[ "$1" != "--force" ]]; then
        echo "First-run already completed."
        echo "Run 'nxs wizard' to reconfigure."
        exit 0
    fi
    
    init_profile_dir
    show_banner
    detect_and_save
    select_roles
    suggest_extensions
    browse_extensions
    finalize
}

# Run
main "$@"
