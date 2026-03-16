#!/bin/bash
# core/lists/system/editor.sh
PROVIDER=$(python3 "$NEXUS_HOME/core/api/module_registry.py" editor)
echo "{\"label\": \"📝 Editor\", \"type\": \"ACTION\", \"payload\": \"$PROVIDER\", \"icon\": \"📝\", \"description\": \"Active Provider: $PROVIDER\"}"
