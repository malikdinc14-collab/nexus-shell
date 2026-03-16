#!/usr/bin/env bash
# core/hud/modules/tabs.sh
# HUD Module: Unified Tab / Stack Provider

# 1. Identify Focused Pane and Role
FOCUSED_INFO=$(tmux display-message -p '#{pane_id}|#{@nexus_role}')
FOCUSED_ID="${FOCUSED_INFO%|*}"
FOCUSED_ROLE="${FOCUSED_INFO#*|}"

[[ -z "$FOCUSED_ROLE" || "$FOCUSED_ROLE" == "null" ]] && exit 0

STACK_DATA=""

if [[ "$FOCUSED_ROLE" == "editor" ]]; then
    # Neovim Tab Provider
    if [[ -S "$NVIM_PIPE" ]]; then
        # Query Nvim for tab list: label:active_flag
        TABS=$(nvim --server "$NVIM_PIPE" --remote-expr "json_encode(map(gettabinfo(), {k,v -> fnamemodify(bufname(v.windows[0]), ':t')}))" 2>/dev/null)
        ACTIVE_IDX=$(nvim --server "$NVIM_PIPE" --remote-expr "tabpagenr()" 2>/dev/null)
        
        # Format for Hudson renderer: [tab1] [tab2*] [tab3]
        if [[ -n "$TABS" && "$TABS" != "null" ]]; then
            STACK_DATA=$(echo "$TABS" | jq -r --arg active "$ACTIVE_IDX" 'to_entries | map(if (.key + 1 | tostring) == $active then "[\(.value)*]" else "[\(.value)]" end) | join(" ")')
        fi
    fi
else
    # General Sovereign Stack Provider
    STACK_JSON=$(/Users/Shared/Projects/nexus-shell/core/stack/nxs-stack list "$FOCUSED_ROLE" 2>/dev/null)
    if [[ -n "$STACK_JSON" && "$STACK_JSON" != "{}" ]]; then
        # Format: [pane1] [pane2*] [pane3]
        STACK_DATA=$(echo "$STACK_JSON" | jq -r '.tabs as $t | .active_index as $a | $t | to_entries | map(if .key == $a then "[\(.value.name)*]" else "[\(.value.name)]" end) | join(" ")')
    fi
fi

if [[ -n "$STACK_DATA" ]]; then
    echo "{\"label\": \"$STACK_DATA\", \"color\": \"BLUE\"}"
fi
