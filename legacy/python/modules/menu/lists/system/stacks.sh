#!/usr/bin/env python3
# modules/menu/lists/system/stacks.sh
import os
import sys
import json
from pathlib import Path

# Discovery
NEXUS_HOME = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[4]))
sys.path.append(str(NEXUS_HOME / "core" / "engine" / "lib"))

try:
    from daemon_client import NexusDaemonClient
    client = NexusDaemonClient()
except ImportError:
    client = None

def get_stacks():
    if not client: return
    res = client.get_state()
    if res.get("status") != "ok": return
    
    state = res.get("data", {})
    
    # We want to show roles as folders
    for role, data in state.items():
        tabs = data.get("tabs", [])
        icon = "📚" if len(tabs) > 1 else "🎴"
        print(json.dumps({
            "label": f"{role} ({len(tabs)})",
            "type": "FOLDER",
            "payload": f"system:stacks:{role}",
            "icon": icon,
            "description": f"Active stack with {len(tabs)} tabs"
        }))

def get_role_tabs(role):
    if not client: return
    res = client.get_state()
    if res.get("status") != "ok": return
    
    state = res.get("data", {})
    if role not in state: return
    
    tabs = state[role].get("tabs", [])
    active_idx = state[role].get("active_index", 0)
    
    for i, tab in enumerate(tabs):
        prefix = "→ " if i == active_idx else "  "
        print(json.dumps({
            "label": f"{prefix}{tab['name']}",
            "type": "STACK_TAB",
            "payload": f"{role}|{i}",
            "icon": "🔖",
            "description": f"Internal ID: {tab['id']}"
        }))

if __name__ == "__main__":
    context = sys.argv[1] if len(sys.argv) > 1 else ""
    
    if context in ["system:stacks", "active_stacks"]:
        get_stacks()
    elif context.startswith("system:stacks:"):
        role = context.replace("system:stacks:", "")
        get_role_tabs(role)
