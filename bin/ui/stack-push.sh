#!/usr/bin/env bash
# stack-push.sh — New tab with type selection (Alt+n)
# Shows a quick capability type picker, then pushes a new tab of that type.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
export PYTHONPATH="$NEXUS_HOME/core:${PYTHONPATH:-}"
export PATH="$NEXUS_HOME/bin:$PATH"

NEXUS_CTL="python3 -m engine.cli.nexus_ctl"

_has() { command -v "$1" &>/dev/null; }

# Quick-pick list of main capability types
TYPES=(
    "terminal\t  Terminal"
    "editor\t  Editor"
    "explorer\t  File Explorer"
    "chat\t  AI Chat"
)

ITEMS=$(printf '%s\n' "${TYPES[@]}")

if _has fzf; then
    SELECTED=$(echo -e "$ITEMS" | fzf \
        --ansi \
        --header=$'\033[36m New Tab\033[0m' \
        --reverse \
        --border=rounded \
        --with-nth=2.. \
        --delimiter=$'\t' \
        --prompt=" > " \
        --height=10 \
        --color='bg+:#1a1f2c,fg+:cyan,hl:yellow,hl+:yellow,border:cyan,header:cyan' \
    ) || exit 0
elif _has gum; then
    LABELS=$(echo -e "$ITEMS" | cut -f2-)
    LABEL=$(echo "$LABELS" | gum filter --header="New Tab" --prompt="> ") || exit 0
    # Find matching type
    SELECTED=$(echo -e "$ITEMS" | grep "$LABEL" | head -1)
    [[ -z "$SELECTED" ]] && exit 0
else
    # Direct push with default type when no interactive tool available
    $NEXUS_CTL stack push 2>/dev/null
    exit $?
fi

CAP_TYPE="$(echo "$SELECTED" | cut -f1)"

if [[ -n "$CAP_TYPE" ]]; then
    $NEXUS_CTL stack push --type "$CAP_TYPE" 2>/dev/null
fi
