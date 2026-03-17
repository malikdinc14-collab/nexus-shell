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
    'roles': data.get('roles', {}),
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
    echo -e "${DIM}Choose which tool to use for each role.${NC}"
    echo -e "${DIM}Press Enter to accept detected value, or type a different tool name.${NC}"
    echo ""
    
    local roles=("editor" "explorer" "chat" "terminal" "viewer" "search")
    local -A role_defaults=(
        ["editor"]="nvim"
        ["explorer"]="yazi"
        ["chat"]="opencode"
        ["terminal"]="zellij"
        ["viewer"]="glow"
        ["search"]="grepai"
    )
    
    local -A role_descriptions=(
        ["editor"]="Code/text editing"
        ["explorer"]="File navigation"
        ["chat"]="AI pair programming"
        ["terminal"]="Terminal enhancements"
        ["viewer"]="Content viewing"
        ["search"]="Code search"
    )
    
    # Load current profile
    local current_roles=$(python3 -c "
import yaml
try:
    with open('$PROFILE_FILE') as f:
        data = yaml.safe_load(f)
    for role, tool in data.get('roles', {}).items():
        print(f'{role}={tool}')
except: pass
")
    
    for role in "${roles[@]}"; do
        local detected=$(echo "$current_roles" | grep "^$role=" | cut -d= -f2)
        local default="${detected:-${role_defaults[$role]}}"
        local desc="${role_descriptions[$role]}"
        
        echo -ne "${WHITE}$role${NC} ($desc): "
        if [[ -n "$detected" ]]; then
            echo -ne "${GREEN}[$detected]${NC}"
        else
            echo -ne "${DIM}[$default]${NC}"
        fi
        echo -ne ": "
        
        read -r user_input
        
        if [[ -n "$user_input" ]]; then
            # User provided custom value
            python3 -c "
import yaml
with open('$PROFILE_FILE') as f:
    data = yaml.safe_load(f)
data['roles']['$role'] = '$user_input'
data['last_modified'] = '$(date -Iseconds)'
with open('$PROFILE_FILE', 'w') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
"
        elif [[ -z "$detected" ]]; then
            # Use default
            python3 -c "
import yaml
with open('$PROFILE_FILE') as f:
    data = yaml.safe_load(f)
data['roles']['$role'] = '$default'
data['last_modified'] = '$(date -Iseconds)'
with open('$PROFILE_FILE', 'w') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
"
        fi
    done
    
    echo ""
    echo -e "${GREEN}✓ Role assignments saved${NC}"
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
