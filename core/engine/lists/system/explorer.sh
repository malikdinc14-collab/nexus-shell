#!/bin/bash
# core/engine/lists/system/explorer.sh
PROVIDER=$(python3 "$NEXUS_HOME/core/engine/api/module_registry.py" explorer)
echo "{\"label\": \"📁 Explorer\", \"type\": \"ACTION\", \"payload\": \"identity:explorer:$PROVIDER\", \"icon\": \"📁\", \"description\": \"Active Provider: $PROVIDER\"}"
