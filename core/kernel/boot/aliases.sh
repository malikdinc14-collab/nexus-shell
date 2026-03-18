#!/bin/bash
# core/kernel/boot/aliases.sh
# Standard shell aliases for Nexus navigation.

alias menu="$NEXUS_KERNEL/exec/switch.sh menu"
alias chat="$NEXUS_KERNEL/exec/switch.sh chat"
alias edit="$NEXUS_KERNEL/exec/switch.sh edit"
alias explorer="$NEXUS_KERNEL/exec/switch.sh explorer"
alias view="$NEXUS_KERNEL/exec/switch.sh view"
alias preview="$NEXUS_KERNEL/exec/preview.sh"

# Geometric Docking (Hiding In-Place)
alias min="$NEXUS_KERNEL/exec/dock.sh toggle"
alias expand="$NEXUS_KERNEL/exec/dock.sh toggle"
alias shelf="$NEXUS_KERNEL/exec/switch.sh shelf"

# Helpful shortcut for the aggregator and system status
alias status="$NEXUS_HOME/core/ui/hud/renderer.sh"
