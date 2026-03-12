#!/usr/bin/env bash
# core/mosaic_select.sh
# A single "Mosaic Cell" representing an open tab.

TYPE="$1"
ID="$2"
TITLE="$3"

# 1. Visual Presentation
clear
echo -e "\033[1;36mMosaic: $TITLE\033[0m"
echo -e "\033[1;30m($TYPE #$ID)\033[0m"
echo "-------------------"

# If it's a file, try to show a preview
if [[ "$TYPE" == "nvim"* ]]; then
    PROJECT_NAME="${NEXUS_PROJECT}"
    NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe"
    # Get the actual path for preview
    # (Simplified for now, could query Nvim for full path)
fi

echo -e "\n\n\033[1;32m>>> CLICK OR PRESS ENTER TO CHOOSE <<<\033[0m"

# 2. Wait for interaction
# In Nexus, the user clicks the pane, which triggers a Tmux-level focus/select.
# But for now, we'll wait for a keypress.
read -r

# 3. Store the selection
echo "$TYPE:$ID" > /tmp/nexus_mosaic_selection

# 4. Trigger the restoration
"${NEXUS_HOME}/core/mosaic_engine.sh" restore
