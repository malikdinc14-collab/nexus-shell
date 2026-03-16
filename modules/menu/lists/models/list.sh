#!/bin/bash
# pillars/models/list.sh
# Pulse Provider for active models (from model-server)

# Try to get active models from local srv
models_json=$(curl -s http://localhost:8000/v1/models)

if [[ $? -ne 0 ]]; then
    # Fallback/Error
    printf '{"label": "Model Server Offline", "type": "DISABLED", "payload": "NONE", "icon": "⚠️"}\n'
    exit 0
fi

# Parse top 5 models using simplest tools (python -c is usually available)
echo "$models_json" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    for m in data.get("data", [])[:10]:
        name = m.get("id")
        print(json.dumps({
            "label": f"🧠 {name}",
            "type": "ACTION",
            "payload": f"nxs-agent-switch-model \"{name}\"",
            "icon": "🧠",
            "description": "Active in srv"
        }))
except:
    pass
'
