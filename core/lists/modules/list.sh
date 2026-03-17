#!/bin/bash
# core/lists/modules/list.sh
# Dynamic provider for IDE roles

cat <<EOF
{"label": "📝 Editor",   "type": "ROLE", "payload": "editor",   "icon": "📝", "description": "Active: $(python3 "$NEXUS_HOME/core/api/module_registry.py" editor)"}
{"label": "📂 Explorer", "type": "ROLE", "payload": "explorer", "icon": "📂", "description": "Active: $(python3 "$NEXUS_HOME/core/api/module_registry.py" explorer)"}
{"label": "💬 Chat",     "type": "ROLE", "payload": "chat",     "icon": "💬", "description": "Active: $(python3 "$NEXUS_HOME/core/api/module_registry.py" chat)"}
{"label": "📺 Viewer",   "type": "ROLE", "payload": "viewer",   "icon": "📺", "description": "Active: $(python3 "$NEXUS_HOME/core/api/module_registry.py" viewer)"}
{"label": "🔍 Search",   "type": "ROLE", "payload": "search",   "icon": "🔍", "description": "Active: $(python3 "$NEXUS_HOME/core/api/module_registry.py" search)"}
{"label": "🖥️ Terminal", "type": "ROLE", "payload": "terminal", "icon": "🖥️", "description": "Active: $(python3 "$NEXUS_HOME/core/api/module_registry.py" terminal)"}
EOF
