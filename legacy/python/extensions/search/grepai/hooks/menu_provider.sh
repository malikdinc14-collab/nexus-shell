#!/usr/bin/env bash
# extensions/grepai/hooks/menu_provider.sh
# Provides menu entries for the Parallax menu system

# Check if grepai is installed
if command -v grepai &>/dev/null; then
    installed="true"
else
    installed="false"
fi

# Output JSON menu entries
cat <<EOF
{"label": "🔍 Semantic Search", "type": "ACTION", "payload": "nxs-grepai search", "icon": "search", "installed": $installed}
{"label": "📊 Trace Callers", "type": "ACTION", "payload": "nxs-grepai trace callers", "icon": "git-branch", "installed": $installed}
{"label": "🔄 Reindex Project", "type": "ACTION", "payload": "nxs-grepai index", "icon": "refresh", "installed": $installed}
{"label": "👁️ Watch Mode", "type": "ACTION", "payload": "nxs-grepai watch", "icon": "eye", "installed": $installed}
EOF
