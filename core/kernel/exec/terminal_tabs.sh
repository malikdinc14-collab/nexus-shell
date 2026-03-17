#!/bin/bash
# core/terminal_tabs.sh
# Manages multiple shell "tabs" within the terminal pane area.
#
# Usage:
#   terminal_tabs.sh new     - Create a new terminal tab
#   terminal_tabs.sh next    - Switch to the next terminal tab
#   terminal_tabs.sh prev    - Switch to the previous terminal tab
#   terminal_tabs.sh list    - List all terminal tabs (for FZF picker)
#
# How it works:
#   All terminal tabs are tmux panes with titles prefixed "term:".
#   Only one is visible at a time — the rest are swapped out.
#   We track them by pane title: term:1, term:2, term:3, etc.

SESSION=$(tmux display-message -p '#S')
TERM_PREFIX="term:"

# Get all panes with our prefix
get_term_panes() {
    tmux list-panes -s -t "$SESSION" -F '#{pane_id} #{pane_title}' 2>/dev/null | \
        grep "$TERM_PREFIX" | sort -t: -k2 -n
}

# Get the currently focused terminal pane
get_active_term() {
    local active_pane
    active_pane=$(tmux display-message -p '#{pane_id}')
    local title
    title=$(tmux display-message -p '#{pane_title}')

    # If we're on a term: pane, return it
    if [[ "$title" == ${TERM_PREFIX}* ]]; then
        echo "$active_pane"
        return
    fi

    # Otherwise find the pane titled "terminal" (the original one)
    tmux list-panes -s -t "$SESSION" -F '#{pane_id} #{pane_title}' | \
        grep "^.*terminal$" | awk '{print $1}' | head -1
}

# Count existing terminal tabs
count_tabs() {
    get_term_panes | wc -l | tr -d ' '
}

# Get next tab number
next_tab_num() {
    local max
    max=$(get_term_panes | awk '{print $2}' | sed "s/$TERM_PREFIX//" | sort -n | tail -1)
    echo $(( ${max:-0} + 1 ))
}

case "${1:-new}" in
    new)
        # Find the current terminal pane
        TERM_PANE=$(tmux list-panes -s -t "$SESSION" -F '#{pane_id} #{pane_title}' | \
            grep -E "(^.*terminal$|^.*${TERM_PREFIX})" | head -1 | awk '{print $1}')

        if [[ -z "$TERM_PANE" ]]; then
            echo "Error: No terminal pane found" >&2
            exit 1
        fi

        # Rename the original terminal pane if it hasn't been renamed yet
        ORIG_TITLE=$(tmux display-message -t "$TERM_PANE" -p '#{pane_title}')
        if [[ "$ORIG_TITLE" == "terminal" ]]; then
            tmux select-pane -t "$TERM_PANE" -T "${TERM_PREFIX}1"
        fi

        # Create a new pane stacked on top of the terminal pane
        NUM=$(next_tab_num)
        NEW_PANE=$(tmux split-window -t "$TERM_PANE" -P -F '#{pane_id}' /bin/zsh -i)
        tmux select-pane -t "$NEW_PANE" -T "${TERM_PREFIX}${NUM}"

        # Resize to fill the terminal area (swap-pane approach)
        tmux swap-pane -s "$NEW_PANE" -t "$TERM_PANE"
        tmux select-pane -t "$TERM_PANE"

        # Zoom the terminal area to hide the old one behind it isn't visible separately
        # Actually just resize — the split should work naturally
        echo "Created terminal tab ${NUM}"
        ;;

    next|prev)
        # Get all terminal pane IDs in order
        PANES=($(get_term_panes | awk '{print $1}'))
        TITLES=($(get_term_panes | awk '{print $2}'))

        if [[ ${#PANES[@]} -le 1 ]]; then
            # Only one tab, nothing to do
            exit 0
        fi

        # Find the currently visible terminal pane
        ACTIVE=$(get_active_term)
        CURRENT_IDX=0
        for i in "${!PANES[@]}"; do
            if [[ "${PANES[$i]}" == "$ACTIVE" ]]; then
                CURRENT_IDX=$i
                break
            fi
        done

        # Calculate the next/prev index
        if [[ "$1" == "next" ]]; then
            TARGET_IDX=$(( (CURRENT_IDX + 1) % ${#PANES[@]} ))
        else
            TARGET_IDX=$(( (CURRENT_IDX - 1 + ${#PANES[@]}) % ${#PANES[@]} ))
        fi

        TARGET="${PANES[$TARGET_IDX]}"

        # Swap the target pane into the visible position
        tmux swap-pane -s "$TARGET" -t "$ACTIVE"
        tmux select-pane -t "$ACTIVE"

        echo "Switched to ${TITLES[$TARGET_IDX]}"
        ;;

    list)
        # Output for FZF picker
        get_term_panes | while read -r pane_id title; do
            cmd=$(tmux display-message -t "$pane_id" -p '#{pane_current_command}')
            echo "${title} (${cmd}) [${pane_id}]"
        done
        ;;
esac
