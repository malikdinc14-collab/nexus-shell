#!/usr/bin/env bash
# core/switcher.sh
# The Master Multimodal Switcher (Alt-m)
# Fuzzy-find and switch between tabs/buffers based on context.

SESSION_ID=$(tmux display-message -p '#S' 2>/dev/null)
PANE_TITLE=$(tmux display-message -p '#{pane_title}')
PANE_ID=$(tmux display-message -p '#{pane_id}')
PROJECT_NAME=$(echo "$SESSION_ID" | sed 's/nexus_//')
NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe"

# 1. Determine Context
if [[ "$PANE_TITLE" == "editor" ]] && [[ -S "$NVIM_PIPE" ]]; then
    # -- NEVIM CONTEXT --
    # Get Nvim tabs via RPC
    TABS=$(nvim --server "$NVIM_PIPE" --remote-expr "JSON.stringify(map(gettabinfo(), {k, v -> v.tabnr . ': ' . fnamemodify(bufname(v.windows[0]), ':t')}))" 2>/dev/null | jq -r '.[]')
    
    if [[ -z "$TABS" ]]; then
        # Fallback to buffers if no tabs
         TABS=$(nvim --server "$NVIM_PIPE" --remote-expr "JSON.stringify(map(filter(getbufinfo({'buflisted':1}), {k, v -> v.name != ''}), {k, v -> v.bufnr . ': ' . fnamemodify(v.name, ':t')}))" 2>/dev/null | jq -r '.[]')
    fi

    CHOICE=$(echo "$TABS" | fzf-tmux -p 60%,40% --header "Nvim: Switch Tab/Buffer" --reverse)
    
    if [[ -n "$CHOICE" ]]; then
        ID=$(echo "$CHOICE" | cut -d: -f1)
        if echo "$CHOICE" | grep -q "Tab"; then
             nvim --server "$NVIM_PIPE" --remote-send "<C-\><C-n>:${ID}tabnext<CR>"
        else
             nvim --server "$NVIM_PIPE" --remote-send "<C-\><C-n>:buffer ${ID}<CR>"
        fi
    fi

elif [[ "$PANE_TITLE" == term:* ]] || [[ "$PANE_TITLE" == "terminal" ]]; then
    # -- TERMINAL TABS CONTEXT --
    TABS=$("${NEXUS_HOME}/core/terminal_tabs.sh" list)
    CHOICE=$(echo "$TABS" | fzf-tmux -p 60%,40% --header "Shell: Switch Tab" --reverse)
    
    if [[ -n "$CHOICE" ]]; then
        TARGET_PANE=$(echo "$CHOICE" | grep -o '\[.*\]' | tr -d '[]')
        tmux swap-pane -s "$TARGET_PANE" -t "$PANE_ID"
        tmux select-pane -t "$PANE_ID"
    fi

else
    # -- GLOBAL CONTEXT: PROJECT SLOTS --
    SLOTS=$(tmux list-windows -t "$SESSION_ID" -F '#I: #{window_name}')
    CHOICE=$(echo "$SLOTS" | fzf-tmux -p 60%,40% --header "Global: Switch project Slot" --reverse)
    
    if [[ -n "$CHOICE" ]]; then
        IDX=$(echo "$CHOICE" | cut -d: -f1)
        tmux select-window -t ":$IDX"
    fi
fi
