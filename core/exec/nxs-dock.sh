#!/bin/bash
# core/exec/nxs-dock.sh
# Collapses or Expands a pane while preserving its proportional height.

ACTION="$1"
LOG_FILE="/tmp/nexus_dock.log"

log() {
    echo "[$(date +'%H:%M:%S')] $1" >> "$LOG_FILE"
}

PANE_ID=$(tmux display-message -p '#{pane_id}')

case "$ACTION" in
    toggle)
        # Check current state
        IS_MINIMIZED=$(tmux display-message -p '#{@nexus_minimized}')
        log "Dock Toggle: Pane=$PANE_ID Minimized=$IS_MINIMIZED"
        
        if [[ "$IS_MINIMIZED" == "1" ]]; then
            # RESTORE
            PREV_VAL=$(tmux display-message -p '#{@nexus_pre_min_val}')
            DIM=$(tmux display-message -p '#{@nexus_min_dim}')
            
            log "Restoring $DIM to: $PREV_VAL"
            if [[ -n "$PREV_VAL" && "$PREV_VAL" != "null" ]]; then
                tmux resize-pane -t "$PANE_ID" -"$DIM" "$PREV_VAL"
                tmux display-message "EXPANDED: $PANE_ID ($PREV_VAL $DIM)"
            fi
            tmux set-option -p -t "$PANE_ID" @nexus_minimized 0
        else
            # MINIMIZE
            CUR_W=$(tmux display-message -p '#{pane_width}')
            CUR_H=$(tmux display-message -p '#{pane_height}')
            
            # Heuristic: Collapse along the smallest dimension relative to its partner
            # Or simpler: if it's tall and thin, collapse X. If it's short and wide, collapse Y.
            if [[ "$CUR_H" -gt "$CUR_W" ]]; then
                DIM="x"
                VAL="$CUR_W"
                TARGET_SIZE=3 # Width for sidebar strip
            else
                DIM="y"
                VAL="$CUR_H"
                TARGET_SIZE=2 # Height for bottom bar
            fi

            log "Minimizing $DIM from: $VAL"
            
            # Avoid minimizing if already at target
            if [[ "$VAL" -le "$TARGET_SIZE" ]]; then
                tmux display-message "Pane already docked ($VAL $DIM)"
                exit 0
            fi

            tmux set-option -p -t "$PANE_ID" @nexus_pre_min_val "$VAL"
            tmux set-option -p -t "$PANE_ID" @nexus_min_dim "$DIM"
            tmux set-option -p -t "$PANE_ID" @nexus_minimized 1
            
            tmux resize-pane -t "$PANE_ID" -"$DIM" "$TARGET_SIZE"
            tmux display-message "DOCKED: $PANE_ID ($TARGET_SIZE $DIM)"
        fi
        ;;
    
    *)
        echo "Usage: nxs-dock toggle"
        exit 1
        ;;
esac
