#!/bin/bash
# core/lists/system/chat.sh
PROVIDER=$(python3 "$NEXUS_HOME/core/api/module_registry.py" chat)
echo "{\"label\": \"💬 AI Chat\", \"type\": \"ACTION\", \"payload\": \"identity:chat:$PROVIDER\", \"icon\": \"💬\", \"description\": \"Active Provider: $PROVIDER\"}"
