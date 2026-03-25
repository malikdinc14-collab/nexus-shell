#!/usr/bin/env bash
# menu-popup.sh — Command Graph menu in fzf (Alt+m)
# Renders the hierarchical command graph as a navigable tree inside a tmux popup.

set -euo pipefail

# Resolve NEXUS_HOME from script location (bin/ui/ -> project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export PYTHONPATH="$NEXUS_HOME/core:${PYTHONPATH:-}"
export PATH="$NEXUS_HOME/bin:$PATH"

# nexus-ctl via Python module (bin/nexus-ctl is a legacy intent resolver)
NEXUS_CTL="python3 -m engine.cli.nexus_ctl"

# ── JSON → fzf helpers ──────────────────────────────────────────────────

_has() { command -v "$1" &>/dev/null; }

# Format menu items for fzf display.
# Each line: "ID\tINDENT ICON  LABEL  (type)"
_format_items() {
    local json="$1"
    if _has jq; then
        echo "$json" | jq -r '
            .items[] |
            ("  " * .depth) as $indent |
            "\(.id)\t\($indent)\(.icon // " ")  \(.label)  \u001b[2m(\(.type))\u001b[0m"
        '
    else
        python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
for item in data.get('items', []):
    indent = '  ' * item.get('depth', 0)
    icon = item.get('icon') or ' '
    label = item.get('label', '')
    ntype = item.get('type', '')
    node_id = item.get('id', '')
    print(f\"{node_id}\t{indent}{icon}  {label}  \033[2m({ntype})\033[0m\")
" <<< "$json"
    fi
}

# Format preview content for a selected node.
_preview_cmd() {
    local json="$1"
    local node_id="$2"
    if _has jq; then
        echo "$json" | jq -r --arg id "$node_id" '
            .items[] | select(.id == $id) |
            "\u001b[36mNode:\u001b[0m      \(.id)",
            "\u001b[36mLabel:\u001b[0m     \(.label)",
            "\u001b[36mType:\u001b[0m      \(.type)",
            "\u001b[36mIcon:\u001b[0m      \(.icon // "none")",
            "\u001b[36mChildren:\u001b[0m  \(.has_children)",
            (if .resolver then "\u001b[36mResolver:\u001b[0m  \(.resolver)" else empty end),
            (if .config_file then "\u001b[36mConfig:\u001b[0m    \(.config_file)" else empty end)
        '
    else
        python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
nid = '$node_id'
for item in data.get('items', []):
    if item.get('id') == nid:
        print(f\"\033[36mNode:\033[0m      {item['id']}\")
        print(f\"\033[36mLabel:\033[0m     {item['label']}\")
        print(f\"\033[36mType:\033[0m      {item['type']}\")
        print(f\"\033[36mIcon:\033[0m      {item.get('icon', 'none')}\")
        print(f\"\033[36mChildren:\033[0m  {item.get('has_children', False)}\")
        if 'resolver' in item:
            print(f\"\033[36mResolver:\033[0m  {item['resolver']}\")
        if 'config_file' in item:
            print(f\"\033[36mConfig:\033[0m    {item['config_file']}\")
        break
" <<< "$json"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────

# Get menu JSON from nexus-ctl
MENU_JSON="$($NEXUS_CTL menu open 2>/dev/null)" || {
    echo "Error: $NEXUS_CTL menu open failed" >&2
    exit 1
}

# Write JSON to temp file for preview access
TMPJSON="$(mktemp)"
echo "$MENU_JSON" > "$TMPJSON"
trap 'rm -f "$TMPJSON"' EXIT

# Format items for fzf
ITEMS="$(_format_items "$MENU_JSON")"

if [[ -z "$ITEMS" ]]; then
    echo "No menu items available."
    exit 0
fi

# Select tool: fzf > gum > bash select
if _has fzf; then
    SELECTED=$(echo "$ITEMS" | fzf \
        --ansi \
        --header=$'\033[36m Nexus Command Graph\033[0m' \
        --reverse \
        --border=rounded \
        --with-nth=2.. \
        --delimiter=$'\t' \
        --preview="bash -c '
            JSON=\"\$(cat \"$TMPJSON\")\"
            ID={1}
            if command -v jq &>/dev/null; then
                echo \"\$JSON\" | jq -r --arg id \"\$ID\" \"
                    .items[] | select(.id == \\\$id) |
                    \\\"\\\\u001b[36mNode:\\\\u001b[0m      \\(.id)\\\",
                    \\\"\\\\u001b[36mLabel:\\\\u001b[0m     \\(.label)\\\",
                    \\\"\\\\u001b[36mType:\\\\u001b[0m      \\(.type)\\\",
                    \\\"\\\\u001b[36mIcon:\\\\u001b[0m      \\(.icon // \\\"none\\\")\\\",
                    \\\"\\\\u001b[36mChildren:\\\\u001b[0m  \\(.has_children)\\\",
                    (if .resolver then \\\"\\\\u001b[36mResolver:\\\\u001b[0m  \\(.resolver)\\\" else empty end),
                    (if .config_file then \\\"\\\\u001b[36mConfig:\\\\u001b[0m    \\(.config_file)\\\" else empty end)
                \"
            else
                echo \"Node: \$ID\"
            fi
        '" \
        --preview-window=right:40%:wrap \
        --prompt=" > " \
        --color='bg+:#1a1f2c,fg+:cyan,hl:yellow,hl+:yellow,border:cyan,header:cyan' \
    ) || exit 0
elif _has gum; then
    # gum fallback: strip ANSI and use gum filter
    PLAIN_ITEMS=$(echo "$ITEMS" | sed 's/\x1b\[[0-9;]*m//g')
    SELECTED=$(echo "$PLAIN_ITEMS" | gum filter --header="Nexus Command Graph" --prompt="> ") || exit 0
else
    # Plain bash select fallback
    echo -e "\033[36m Nexus Command Graph\033[0m"
    echo ""
    mapfile -t LINES <<< "$ITEMS"
    select LINE in "${LINES[@]}"; do
        SELECTED="$LINE"
        break
    done
    [[ -z "${SELECTED:-}" ]] && exit 0
fi

# Extract the node ID (first tab-delimited field)
NODE_ID="$(echo "$SELECTED" | cut -f1)"

if [[ -z "$NODE_ID" ]]; then
    exit 0
fi

# Check if this is a group node (has children) — relaunch with subtree
HAS_CHILDREN="false"
if _has jq; then
    HAS_CHILDREN="$(echo "$MENU_JSON" | jq -r --arg id "$NODE_ID" '.items[] | select(.id == $id) | .has_children')"
else
    HAS_CHILDREN="$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
nid = '$NODE_ID'
for item in data.get('items', []):
    if item.get('id') == nid:
        print(str(item.get('has_children', False)).lower())
        break
" <<< "$MENU_JSON")"
fi

if [[ "$HAS_CHILDREN" == "true" ]]; then
    # Group node: re-open menu filtered to this subtree
    # TODO: implement subtree navigation
    $NEXUS_CTL menu select "$NODE_ID" 2>/dev/null
else
    # Leaf node: dispatch through daemon — NexusCore resolves and executes
    DAEMON_CLIENT="$NEXUS_HOME/core/engine/lib/daemon_client.py"
    SELECT_RESULT=$(python3 "$DAEMON_CLIENT" menu_select "{\"node_id\": \"$NODE_ID\"}" 2>/dev/null) || true

    # [INVARIANT] Verify dispatch succeeded
    if [[ -n "$SELECT_RESULT" ]]; then
        STATUS=$(echo "$SELECT_RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
        if [[ "$STATUS" != "ok" ]]; then
            echo "[menu-popup] Dispatch failed: $SELECT_RESULT" >&2
        fi
    else
        echo "[menu-popup] [INVARIANT] No response from daemon menu_select" >&2
    fi
fi
