#!/bin/bash
# core/kernel/exec/nxs-onboard.sh
# Interactive Training Component for Nexus Onboarding.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Aesthetic helper
print_step() {
    clear
    echo -e "\033[1;36m[ THE ASCENT: PHASE $1 ]\033[0m"
    echo -e "\033[1;37m$2\033[0m"
    echo "------------------------------------------------"
}

# 1. Navigation
print_step "1" "MASTERING THE HIERARCHY"
echo "Nexus uses a dual-layer tab system."
echo "Level 1: Nexus-Tabs (Workspace Stacks)"
echo "Level 2: Pane-Tabs (Tool Stacks)"
echo ""
echo "TASK: Create a new Nexus-Tab (Alt-T)."
echo "Then, cycle back here using Alt-Shift-[ or ]."
echo ""
read -p "Press ENTER once you have successfully cycled back..."

# 2. AI Cockpit
print_step "2" "THE SOVEREIGN MIND"
echo "Your AI partner (Pi) is integrated into the core."
echo "TASK: Open the AI Cockpit (Home > Sovereignty > AI & Models)."
echo "Select 'Start Link to Pi' and observe the terminal below."
echo ""
read -p "Press ENTER once you see Pi initializing..."

# 3. GAP Alignment
print_step "3" "GATED AUTONOMY"
echo "All work is governed by the Gated Agent Protocol."
echo "Mission specs are verified before a single line of code is written."
echo ""
echo "TASK: Launch 'GAP Mission Control' from the AI menu."
echo "Explore the multi-tab Spec Manager that appears."
echo ""
read -p "Press ENTER to complete certification..."

clear
echo -e "\033[1;32m[ CERTIFICATION COMPLETE ]\033[0m"
echo "Architect: $(whoami)"
echo "System: Nexus Shell"
echo "Status: ALIGNED"
echo ""
echo "Your ascent is authorized. LFG."
echo ""
sleep 3
# Close onboarding
tmux kill-window
