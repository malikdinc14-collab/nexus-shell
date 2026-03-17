#!/bin/bash
# core/kernel/boot/nxs-aliases.sh
# Standard shell aliases for Nexus navigation.

alias menu="$NEXUS_HOME/core/kernel/exec/nxs-switch.sh menu"
alias chat="$NEXUS_HOME/core/kernel/exec/nxs-switch.sh chat"
alias edit="$NEXUS_HOME/core/kernel/exec/nxs-switch.sh edit"
alias explorer="$NEXUS_HOME/core/kernel/exec/nxs-switch.sh explorer"
alias view="$NEXUS_HOME/core/kernel/exec/nxs-switch.sh view"
alias preview="$NEXUS_HOME/core/kernel/exec/nxs-preview.sh"

# Geometric Docking (Hiding In-Place)
alias min="$NEXUS_HOME/core/kernel/exec/nxs-dock.sh toggle"
alias expand="$NEXUS_HOME/core/kernel/exec/nxs-dock.sh toggle"
alias shelf="$NEXUS_HOME/core/kernel/exec/nxs-switch.sh shelf"

# Helpful shortcut for the aggregator and system status
alias nxs-status="$NEXUS_HOME/core/ui/hud/renderer.sh"
