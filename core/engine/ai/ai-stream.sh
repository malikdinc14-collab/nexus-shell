#!/bin/bash
# Nexus AI Stream Monitor
# Pretty-prints real-time AI thoughts and tool logs from the Event Bus.

echo -e "\033[1;35m[*] NEXUS AI STREAM ACTIVE\033[0m"
echo -e "\033[0;90mListening for AI_STREAM and AI_EVENT...\033[0m"
echo "------------------------------------------------"

nxs-event subscribe AI_STREAM | while read -r event; do
    TEXT=$(echo "$event" | jq -r '.data.text // empty')
    if [[ -n "$TEXT" ]]; then
        # Check if it's a tool call or thought
        if [[ "$TEXT" == *">"* ]]; then
            echo -e "\033[1;36m$TEXT\033[0m"
        elif [[ "$TEXT" == *"["* ]]; then
            echo -e "\033[1;33m$TEXT\033[0m"
        else
            echo "$TEXT"
        fi
    fi
done
