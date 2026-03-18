#!/bin/bash
# core/kernel/exec/tabs.sh
# Universal Modular Tab Engine for Nexus Shell
# Allows any module role (Chat, Terminal, Editor, Tools, etc.) to host multiple tabs.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
SESSION=$(tmux display-message -p '#S')

ROLE="${1}"      # e.g., "chat", "terminal", "nexus-shell"
ACTION="${2:-next}" # new, next, prev, list, close
CMD="${3}"          # optional command for 'new'

# If role is not provided, try to detect it from pane title
if [[ -z "$ROLE" ]]; then
    TITLE=$(tmux display-message -p '#{pane_title}')
    ROLE=$(echo "$TITLE" | cut -d':' -f1 | tr -d '[] ')
fi

# Fallback to terminal if still empty
ROLE="${ROLE:-terminal}"
TAB_PREFIX="${ROLE}:"

# Get all panes belonging to the role stack
get_stack_panes() {
    tmux list-panes -s -t "$SESSION" -F '#{pane_id} #{pane_title}' 2>/dev/null | \
        grep "$TAB_PREFIX" | sort -t: -k2 -n
}

# Get the currently visible pane for this role
get_visible_pane() {
    local active_id=$(tmux display-message -p '#{pane_id}')
    local active_title=$(tmux display-message -p '#{pane_title}')
    
    # If the active pane IS a member of this role's stack, it's the visible one
    if [[ "$active_title" == ${TAB_PREFIX}* ]]; then
        echo "$active_id"
    else
        # Otherwise, find the "master" pane for this role
        # We assume the master is either titled the role name exactly, or is the first in the stack
        tmux list-panes -s -t "$SESSION" -F '#{pane_id} #{pane_title}' | \
            grep -E "(^.* ${ROLE}$|^.* ${TAB_PREFIX})" | head -1 | awk '{print $1}'
    fi
}

case "$ACTION" in
    new)
        VISIBLE=$(get_visible_pane)
        if [[ -z "$VISIBLE" ]]; then
            echo "[!] Error: Role '$ROLE' not found in current layout." >&2
            exit 1
        fi

        # Determine next ID
        MAX_ID=$(get_stack_panes | awk '{print $2}' | sed "s/$TAB_PREFIX//" | sort -n | tail -1)
        NEXT_ID=$(( ${MAX_ID:-1} + 1 ))

        # If it's the first tab creation, rename the visible one to Tab 1
        VISIBLE_TITLE=$(tmux display-message -t "$VISIBLE" -p '#{pane_title}')
        if [[ "$VISIBLE_TITLE" == "$ROLE" ]]; then
            tmux select-pane -t "$VISIBLE" -T "${TAB_PREFIX}1"
            NEXT_ID=2
        fi

        # Split and start a new shell (or tool)
        NEW_CMD="${CMD:-/bin/zsh}"
        NEW_PANE=$(tmux split-window -t "$VISIBLE" -d -P -F '#{pane_id}' "$NEW_CMD")
        tmux select-pane -t "$NEW_PANE" -T "${TAB_PREFIX}${NEXT_ID}"

        # Bring into view
        tmux swap-pane -s "$NEW_PANE" -t "$VISIBLE"
        tmux select-pane -t "$VISIBLE"
        ;;

    next|prev)
        PANES=($(get_stack_panes | awk '{print $1}'))
        TITLES=($(get_stack_panes | awk '{print $2}'))
        VISIBLE=$(get_visible_pane)

        if [[ ${#PANES[@]} -le 1 ]]; then exit 0; fi

        CURRENT_IDX=-1
        for i in "${!PANES[@]}"; do
            if [[ "${PANES[$i]}" == "$VISIBLE" ]]; then
                CURRENT_IDX=$i
                break
            fi
        done

        if [[ $CURRENT_IDX -eq -1 ]]; then exit 1; fi

        if [[ "$ACTION" == "next" ]]; then
            TARGET_IDX=$(( (CURRENT_IDX + 1) % ${#PANES[@]} ))
        else
            TARGET_IDX=$(( (CURRENT_IDX - 1 + ${#PANES[@]}) % ${#PANES[@]} ))
        fi

        TARGET="${PANES[$TARGET_IDX]}"
        tmux swap-pane -s "$TARGET" -t "$VISIBLE"
        tmux select-pane -t "$VISIBLE"
        ;;

    nexus-next|nexus-prev)
        # LEVEL 1: Nexus-Tabs (Window/Workspace Stacks)
        # These are tmux windows within the current slot group
        local slot=$(tmux display-message -p '#I' | cut -d':' -f1)
        local windows=($(tmux list-windows -F '#I' | grep "^${slot}:"))
        local current=$(tmux display-message -p '#I')
        
        if [[ ${#windows[@]} -le 1 ]]; then exit 0; fi
        
        local idx=-1
        for i in "${!windows[@]}"; do
            if [[ "${windows[$i]}" == "$current" ]]; then
                idx=$i
                break
            fi
        done
        
        if [[ "$ACTION" == "nexus-next" ]]; then
            target_idx=$(( (idx + 1) % ${#windows[@]} ))
        else
            target_idx=$(( (idx - 1 + ${#windows[@]}) % ${#windows[@]} ))
        fi
        
        tmux select-window -t "${windows[$target_idx]}"
        ;;

    list)
        get_stack_panes
        ;;

    close)
        VISIBLE=$(get_visible_pane)
        COUNT=$(get_stack_panes | wc -l)
        if [[ $COUNT -gt 1 ]]; then
            # Cycle to another tab before closing this one
            $0 "$ROLE" next
            tmux kill-pane -t "$VISIBLE"
        fi
        ;;
esac
