#!/usr/bin/env bash
# capability-popup.sh — Capability launcher in fzf (Alt+o)
# Lists available capabilities and their adapters for interactive selection.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export PYTHONPATH="$NEXUS_HOME/core:${PYTHONPATH:-}"
export PATH="$NEXUS_HOME/bin:$PATH"

NEXUS_CTL="python3 -m engine.cli.nexus_ctl"

_has() { command -v "$1" &>/dev/null; }

# Format capabilities for fzf.
# Each line: "TYPE\tADAPTER\t label  (adapter_name)  [default]"
_format_capabilities() {
    local json="$1"
    if _has jq; then
        echo "$json" | jq -r '
            .capabilities[] |
            .type as $type | .label as $label | .default as $def |
            .adapters[] |
            if .available then
                "\($type)\t\(.name)\t\u001b[36m\($label)\u001b[0m  \u001b[37m(\(.name))\u001b[0m" +
                (if .name == $def then "  \u001b[33m[default]\u001b[0m" else "" end)
            else empty end
        '
    else
        python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
for cap in data.get('capabilities', []):
    ctype = cap['type']
    label = cap['label']
    default = cap.get('default', '')
    for adapter in cap.get('adapters', []):
        if adapter.get('available'):
            name = adapter['name']
            marker = '  \033[33m[default]\033[0m' if name == default else ''
            print(f\"{ctype}\t{name}\t\033[36m{label}\033[0m  \033[37m({name})\033[0m{marker}\")
" <<< "$json"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────

CAP_JSON="$($NEXUS_CTL capability open 2>/dev/null)" || {
    echo "Error: $NEXUS_CTL capability open failed" >&2
    exit 1
}

ITEMS="$(_format_capabilities "$CAP_JSON")"

if [[ -z "$ITEMS" ]]; then
    echo "No capabilities available."
    exit 0
fi

if _has fzf; then
    SELECTED=$(echo "$ITEMS" | fzf \
        --ansi \
        --header=$'\033[36m Nexus Capability Launcher\033[0m' \
        --reverse \
        --border=rounded \
        --with-nth=3.. \
        --delimiter=$'\t' \
        --prompt=" > " \
        --color='bg+:#1a1f2c,fg+:cyan,hl:yellow,hl+:yellow,border:cyan,header:cyan' \
    ) || exit 0
elif _has gum; then
    PLAIN=$(echo "$ITEMS" | sed 's/\x1b\[[0-9;]*m//g')
    SELECTED=$(echo "$PLAIN" | gum filter --header="Nexus Capabilities" --prompt="> ") || exit 0
else
    echo -e "\033[36m Nexus Capability Launcher\033[0m"
    echo ""
    mapfile -t LINES <<< "$ITEMS"
    select LINE in "${LINES[@]}"; do
        SELECTED="$LINE"
        break
    done
    [[ -z "${SELECTED:-}" ]] && exit 0
fi

# Extract type and adapter from tab-delimited fields
CAP_TYPE="$(echo "$SELECTED" | cut -f1)"
ADAPTER="$(echo "$SELECTED" | cut -f2)"

if [[ -n "$CAP_TYPE" && -n "$ADAPTER" ]]; then
    $NEXUS_CTL capability select "$CAP_TYPE" --adapter "$ADAPTER" 2>/dev/null
fi
