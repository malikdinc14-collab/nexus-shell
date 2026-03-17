#!/bin/bash
# core/kernel/boot/setup_wizard.sh
# The Universal Installation & Configuration Wizard for Nexus Shell.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
MODULES_DIR="$NEXUS_HOME/modules"
CONFIG_FILE="$NEXUS_HOME/config/modules.conf"

# ANSI Color Codes
CYAN='\033[1;36m'
WHITE='\033[1;37m'
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
GRAY='\033[0;90m'
NC='\033[0m'

clear
echo -e "${CYAN}"
echo "    _   _  _______  __  _  _  _____"
echo "   | \ | ||  ____ ||  || | ||  ___|"
echo "   |  \| || |__    |  || | || |___ "
echo "   | .   ||  __|   |  || | ||___  |"
echo "   | |\  || |____  \  \/  /  ___| |"
echo "   |_| \_||_______| \____/  |_____|"
echo -e "${NC}"
echo -e "${WHITE}    >>> LOADING UNIVERSAL SETUP WIZARD...${NC}"
echo -e "${GRAY}    ------------------------------------------${NC}"
sleep 1

# --- Step 1: Tool Selection (Pick Your Toolkit) ---
echo -e "\n${CYAN}🎯 PHASE 1: PICK YOUR TOOLKIT${NC}"
echo -e "${GRAY}Select the modules you want to enable for this workstation.${NC}"
echo -e "${GRAY}(Use [Tab] to select multiple, [Enter] to confirm)${NC}\n"
sleep 1

# Discover all modules with manifests
TOOL_LIST=$(ls -d "$MODULES_DIR"/*/ 2>/dev/null | while read d; do
    manifest="$d/manifest.json"
    name=$(basename "$d")
    if [[ -f "$manifest" ]]; then
        desc=$(grep '"description"' "$manifest" | cut -d'"' -f4)
        echo "$name | $desc"
    else
        echo "$name | (No description)"
    fi
done)

SELECTED_TOOLS=$(echo "$TOOL_LIST" | fzf --multi --ansi \
    --header="NEXUS MODULE SELECTOR" \
    --prompt="Enable > " \
    --preview 'echo {} | cut -d"|" -f2' \
    --preview-window=bottom:3:wrap \
    --color="header:cyan,prompt:yellow,pointer:green,hl:cyan" | cut -d'|' -f1 | xargs)

if [[ -z "$SELECTED_TOOLS" ]]; then
    echo -e "${YELLOW}[!] No tools selected. Using minimal core only.${NC}"
else
    echo -e "${GREEN}[+] Enabling ${#SELECTED_TOOLS[@]} tools...${NC}"
    echo "$SELECTED_TOOLS" > "$CONFIG_FILE"
fi

# --- Step 2: System Dependency Check ---
echo -e "\n${CYAN}⚙️ PHASE 2: SYSTEM DEPENDENCIES${NC}"
print_check() {
    echo -ne "    ${GRAY}[*] Checking $1...${NC}"
    if command -v "$2" &>/dev/null; then
        echo -e " ${GREEN}OK${NC}"
    else
        echo -e " ${YELLOW}MISSING${NC}"
        MISSING_DEPS+=("$1 ($2)")
    fi
}

print_check "Node.js" "node"
print_check "Python 3" "python3"
print_check "FZF" "fzf"
print_check "Bat" "bat"
print_check "Glow" "glow"
print_check "Carbonyl (Web)" "carbonyl"
print_check "Grip (MD)" "grip"
print_check "Marimo (DS)" "marimo"

if [[ -n "$MISSING_DEPS" ]]; then
    echo -e "\n${YELLOW}[!] Warning: Some global dependencies are missing.${NC}"
    echo -e "    ${GRAY}Tools relying on these might not function correctly until installed.${NC}"
fi

# --- Step 3: AI Partner (Pi) Configuration ---
echo -e "\n${CYAN}🤖 PHASE 3: AI PARTNER SETUP (PI)${NC}"
echo -ne "Would you like to install the Pi AI Coding Agent now? (y/N): "
read -r setup_pi

if [[ "$setup_pi" =~ ^[Yy]$ ]]; then
    PI_DIR="$NEXUS_HOME/modules/pi-mono"
    echo -e "${YELLOW}[*] Installing Pi dependencies (Local)...${NC}"
    if [[ ! -d "$PI_DIR/node_modules" ]]; then
        (cd "$PI_DIR" && npm install && npm run build)
        if [[ $? -eq 0 ]]; then
            echo -e "${GREEN}[+] Pi is ready to brief.${NC}"
        else
            echo -e "${RED}[!] Pi installation failed.${NC}"
        fi
    else
        echo -e "${GREEN}[+] Pi already installed.${NC}"
    fi
else
    echo -e "${GRAY}Skipping AI setup. You can run 'nxs-pi-setup' later.${NC}"
fi

# --- Finalization ---
echo -e "\n${GREEN}🚀 SETUP COMPLETE.${NC}"
echo -e "${GRAY}Your configuration has been saved to config/modules.conf.${NC}"
echo -e "${WHITE}Initializing your custom workspace...${NC}"
sleep 2
