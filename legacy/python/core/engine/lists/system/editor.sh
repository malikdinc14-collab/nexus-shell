#!/bin/bash
# core/engine/lists/system/editor.sh
PROVIDER=$(python3 "$NEXUS_HOME/core/engine/api/module_registry.py" editor)
echo "{\"label\": \"📝 Editor\", \"type\": \"ACTION\", \"payload\": \"identity:editor:$PROVIDER\", \"icon\": \"📝\", \"description\": \"Active Provider: $PROVIDER\"}"
