#!/usr/bin/env bash
# core/ui/hud/modules/tabs.sh
# HUD Module: Unified Tab / Stack Provider
# Uses action layer for pane metadata, stack client for stack state.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

# 1. Get focused pane info via action layer
FOCUSED_ID=$("$PY" "$DISPATCH" pane.id 2>/dev/null)
FOCUSED_ROLE=$("$PY" "$DISPATCH" pane.metadata "$FOCUSED_ID" "@nexus_role" 2>/dev/null)

[[ -z "$FOCUSED_ROLE" || "$FOCUSED_ROLE" == "null" ]] && exit 0

STACK_DATA=""

if [[ "$FOCUSED_ROLE" == "editor" ]]; then
    # Neovim Tab Provider — uses editor adapter via dispatch
    TABS=$("$PY" "$DISPATCH" editor.tabs 2>/dev/null)
    if [[ -n "$TABS" && "$TABS" != "[]" ]]; then
        STACK_DATA=$(echo "$TABS" | jq -r 'to_entries | map("[\(.value.name // .value)]") | join(" ")' 2>/dev/null)
    fi
else
    # General Sovereign Stack Provider — uses stack client (already adapter-clean)
    STACK_JSON=$("$NEXUS_HOME/core/kernel/stack/stack" list "$FOCUSED_ROLE" 2>/dev/null)
    if [[ -n "$STACK_JSON" && "$STACK_JSON" != "{}" ]]; then
        STACK_DATA=$(echo "$STACK_JSON" | jq -r '.tabs as $t | .active_index as $a | $t | to_entries | map(if .key == $a then "[\(.value.name)*]" else "[\(.value.name)]" end) | join(" ")')
    fi
fi

if [[ -n "$STACK_DATA" ]]; then
    echo "{\"label\": \"$STACK_DATA\", \"color\": \"BLUE\"}"
fi
