#!/bin/bash
# core/kernel/boot/onboarding.sh
# The "Ascent" Intro Spectacle for Nexus Shell.

# ANSI Color Codes
CYAN='\033[1;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m'

clear

# 1. The Branding (Faded reveal simulation)
echo -e "${GRAY}"
echo "    _   _  _______  __  _  _  _____"
echo "   | \ | ||  ____ ||  || | ||  ___|"
echo "   |  \| || |__    |  || | || |___ "
echo "   | .   ||  __|   |  || | ||___  |"
echo "   | |\  || |____  \  \/  /  ___| |"
echo "   |_| \_||_______| \____/  |_____|"
echo -e "${NC}"
sleep 1

echo -e "${CYAN}    >>> INITIALIZING THE ASCENT...${NC}"
sleep 0.5

# 2. Pre-flight Checks
print_check() {
    echo -e -n "    ${GRAY}[*] Checking $1...${NC}"
    sleep 0.3
    echo -e " ${CYAN}OK${NC}"
}

print_check "Keychain Authority"
print_check "Safety Guard Protocols"
print_check "Sovereign Inference Links"
print_check "GAP Mission Sync"
sleep 0.5

# 3. Universal Setup Wizard
echo ""
echo -e "${CYAN}    >>> STARTING UNIVERSAL SETUP WIZARD...${NC}"
bash "$NEXUS_HOME/core/kernel/boot/setup_wizard.sh"
sleep 1

echo ""
echo -e "${WHITE}    Welcome, Architect.${NC}"
echo -e "${GRAY}    Your sovereign workstation is now online.${NC}"
echo ""
sleep 1

# 3. Launch the Grounds
echo -e "${CYAN}    >>> LOADING TRAINING GROUNDS...${NC}"
sleep 1

# Launch the onboarding composition in a new window
# Note: We assume nxs-launcher --comp will handle this correctly
tmux new-window -n "The:Ascent" "nxs-launcher --comp onboarding"
