#!/bin/bash
# modules/menu/lists/settings/list.sh

echo "{\"label\": \"Dashboard (Global)\", \"type\": \"ACTION\", \"payload\": \"$NEXUS_HOME/modules/menu/config/home.yaml\", \"verb\": \"edit\", \"icon\": \"🌍\"}"
if [ -n "$NEXUS_PROFILE" ]; then
    echo "{\"label\": \"Dashboard (Profile)\", \"type\": \"ACTION\", \"payload\": \"$NEXUS_HOME/config/profiles/$NEXUS_PROFILE/home.yaml\", \"verb\": \"edit\", \"icon\": \"👤\"}"
fi
echo "{\"label\": \"Dashboard (Workspace)\", \"type\": \"ACTION\", \"payload\": \"$PROJECT_ROOT/.nexus/home.yaml\", \"verb\": \"edit\", \"icon\": \"💻\"}"
echo "{\"label\": \"Registry Explorer\", \"type\": \"PLANE\", \"payload\": \"global:\", \"icon\": \"🗃️\"}"
echo "{\"label\": \"Action Audit\", \"type\": \"ACTION\", \"payload\": \"$NEXUS_HOME/config/actions.yaml\", \"verb\": \"edit\", \"icon\": \"⚡\"}"
