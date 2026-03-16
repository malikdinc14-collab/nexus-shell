#!/bin/bash
# core/lists/system/explorer.sh
PROVIDER=$(python3 "$NEXUS_HOME/core/api/module_registry.py" explorer)
echo "{\"label\": \"📁 Explorer\", \"type\": \"ACTION\", \"payload\": \"$PROVIDER\", \"icon\": \"📁\", \"description\": \"Active Provider: $PROVIDER\"}"
