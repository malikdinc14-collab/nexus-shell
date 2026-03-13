#!/bin/bash
# Nexus AI Query Tool
# Sends a mission/question to the Sovereign Intelligence Daemon via the Event Bus.

QUERY="$*"

if [[ -z "$QUERY" ]]; then
    echo "Usage: nxs-ask <your question or mission>"
    exit 1
fi

# Send the query as an AI_QUERY event
nxs-event publish AI_QUERY "{\"query\": \"$QUERY\", \"cwd\": \"$(pwd)\"}"

echo -e "\033[0;90m[nxs-ask] Query dispatched to SID. Watch 'nxs-ai-stream' for progress.\033[0m"
