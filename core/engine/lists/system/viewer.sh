#!/bin/bash
# core/engine/lists/system/viewer.sh
PROVIDER=$(python3 "$NEXUS_HOME/core/engine/api/module_registry.py" viewer)
echo "{\"label\": \"🔍 Viewer\", \"type\": \"ACTION\", \"payload\": \"$PROVIDER\", \"icon\": \"🔍\", \"description\": \"Active Provider: $PROVIDER\"}"
