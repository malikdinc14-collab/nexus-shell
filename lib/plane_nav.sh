#!/usr/bin/env zsh
# scripts/plane_nav.sh
# Coordinate-based 2D navigation for Nexus-Shell 5-pane layout

DIRECTION=$1
CUR_PANE_ID=$(tmux display-message -p '#{pane_id}')
CUR_PANE_INDEX=$(tmux display-message -p '#{pane_index}')

# Use exported indices from launcher.sh, fallback to standard layout
TREE=${PX_NEXUS_TREE_PANE:-0}
PARALLAX=${PX_NEXUS_PARALLAX_PANE:-1}
EDITOR=${PX_NEXUS_EDITOR_PANE:-2}
TERMINAL=${PX_NEXUS_TERMINAL_PANE:-3}
CHAT=${PX_NEXUS_CHAT_PANE:-4}

case "$DIRECTION" in
    "up")
        if [[ "$CUR_PANE_INDEX" == "$TERMINAL" ]]; then
            tmux select-pane -t "$EDITOR"
        elif [[ "$CUR_PANE_INDEX" == "$EDITOR" ]]; then
            tmux select-pane -t "$PARALLAX"
        fi
        ;;
    "down")
        if [[ "$CUR_PANE_INDEX" == "$PARALLAX" ]]; then
            tmux select-pane -t "$EDITOR"
        elif [[ "$CUR_PANE_INDEX" == "$EDITOR" ]]; then
            tmux select-pane -t "$TERMINAL"
        fi
        ;;
    "left")
        if [[ "$CUR_PANE_INDEX" == "$CHAT" ]]; then
            tmux select-pane -t "$EDITOR"
        elif [[ "$CUR_PANE_INDEX" == "$PARALLAX" || "$CUR_PANE_INDEX" == "$EDITOR" || "$CUR_PANE_INDEX" == "$TERMINAL" ]]; then
            tmux select-pane -t "$TREE"
        fi
        ;;
    "right")
        if [[ "$CUR_PANE_INDEX" == "$TREE" ]]; then
            tmux select-pane -t "$EDITOR"
        elif [[ "$CUR_PANE_INDEX" == "$PARALLAX" || "$CUR_PANE_INDEX" == "$EDITOR" || "$CUR_PANE_INDEX" == "$TERMINAL" ]]; then
            tmux select-pane -t "$CHAT"
        fi
        ;;
esac
