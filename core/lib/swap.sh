#!/bin/bash
# lib/swap.sh
# Legacy wrapper for the new Nexus Editor Toggle.

NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
"$NEXUS_HOME/modules/editor/bin/nxs-editor" toggle
