#!/usr/bin/env bash
# tab-switcher.sh — Tab list/switcher in fzf (Alt+t)
# Lists tabs in the current pane's stack for interactive switching.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export PYTHONPATH="$NEXUS_HOME/core:${PYTHONPATH:-}"
export PATH="$NEXUS_HOME/bin:$PATH"

NEXUS_CTL="python3 -m engine.cli.nexus_ctl"

_has() { command -v "$1" &>/dev/null; }

# Format tabs for fzf.
# Each line: "INDEX\t [index] type:adapter (role)  *active*"
_format_tabs() {
    local json="$1"
    if _has jq; then
        echo "$json" | jq -r '
            .active_index as $active |
            .tabs | to_entries[] |
            .key as $idx | .value |
            "\($idx)\t" +
            (if $idx == $active then "\u001b[33m>\u001b[0m " else "  " end) +
            "\u001b[36m[\($idx)]\u001b[0m " +
            "\u001b[37m\(.type):\(.adapter)\u001b[0m " +
            "\u001b[2m(\(.role))\u001b[0m" +
            (if $idx == $active then "  \u001b[33m[active]\u001b[0m" else "" end)
        '
    else
        python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
active = data.get('active_index', 0)
for i, tab in enumerate(data.get('tabs', [])):
    marker = '\033[33m>\033[0m ' if i == active else '  '
    active_tag = '  \033[33m[active]\033[0m' if i == active else ''
    print(f\"{i}\t{marker}\033[36m[{i}]\033[0m \033[37m{tab['type']}:{tab['adapter']}\033[0m \033[2m({tab['role']})\033[0m{active_tag}\")
" <<< "$json"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────

TABS_JSON="$($NEXUS_CTL tabs list 2>/dev/null)" || {
    echo "Error: $NEXUS_CTL tabs list failed" >&2
    exit 1
}

ITEMS="$(_format_tabs "$TABS_JSON")"

if [[ -z "$ITEMS" ]]; then
    echo "No tabs in current stack."
    exit 0
fi

if _has fzf; then
    SELECTED=$(echo "$ITEMS" | fzf \
        --ansi \
        --header=$'\033[36m Nexus Tab Switcher\033[0m' \
        --reverse \
        --border=rounded \
        --with-nth=2.. \
        --delimiter=$'\t' \
        --prompt=" > " \
        --color='bg+:#1a1f2c,fg+:cyan,hl:yellow,hl+:yellow,border:cyan,header:cyan' \
    ) || exit 0
elif _has gum; then
    PLAIN=$(echo "$ITEMS" | sed 's/\x1b\[[0-9;]*m//g')
    SELECTED=$(echo "$PLAIN" | gum filter --header="Nexus Tabs" --prompt="> ") || exit 0
else
    echo -e "\033[36m Nexus Tab Switcher\033[0m"
    echo ""
    mapfile -t LINES <<< "$ITEMS"
    select LINE in "${LINES[@]}"; do
        SELECTED="$LINE"
        break
    done
    [[ -z "${SELECTED:-}" ]] && exit 0
fi

# Extract tab index from first field
TAB_INDEX="$(echo "$SELECTED" | cut -f1)"

if [[ -n "$TAB_INDEX" ]]; then
    $NEXUS_CTL tabs jump "$TAB_INDEX" 2>/dev/null
fi
