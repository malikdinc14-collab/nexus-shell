#!/bin/bash
# core/kernel/exec/nxs-dock.sh
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
            if [[ "$DIM" == "zoom" ]]; then
                tmux resize-pane -t "$PANE_ID" -Z
                tmux display-message "EXPANDED: $PANE_ID (ZOOMED)"
            elif [[ -n "$PREV_VAL" && "$PREV_VAL" != "null" ]]; then
                tmux resize-pane -t "$PANE_ID" -"$DIM" "$PREV_VAL"
                tmux display-message "EXPANDED: $PANE_ID ($PREV_VAL $DIM)"
            fi
            tmux set-option -p -t "$PANE_ID" @nexus_minimized 0
        else
            # MINIMIZE
            CUR_W=$(tmux display-message -p '#{pane_width}')
            CUR_H=$(tmux display-message -p '#{pane_height}')
            
            # Smart Orientation Check
            if [[ "$CUR_H" -gt "$CUR_W" ]]; then
                # Vertical Sidebar: Minimize to strip, restore via zoom
                log "Minimizing Vertical Sidebar to strip (restore via zoom)"
                
                # Store current width and set restore dimension to 'zoom'
                tmux set-option -p -t "$PANE_ID" @nexus_pre_min_val "$CUR_W"
                tmux set-option -p -t "$PANE_ID" @nexus_min_dim "zoom"
                tmux set-option -p -t "$PANE_ID" @nexus_minimized 1
                
                # Collapse to a narrow strip
                DIM="x"
                TARGET_SIZE=3
                
                # Avoid minimizing if already at target
                if [[ "$CUR_W" -le "$TARGET_SIZE" ]]; then
                    tmux display-message "Pane already docked ($CUR_W $DIM)"
                    exit 0
                fi

                tmux resize-pane -t "$PANE_ID" -"$DIM" "$TARGET_SIZE"
            else
                # Horizontal Bottom Bar: Minimize to strip, restore proportionally
                DIM="y"
                VAL="$CUR_H"
                TARGET_SIZE=2
                log "Minimizing Horizontal Bar from: $VAL"
                
                # Avoid minimizing if already at target
                if [[ "$VAL" -le "$TARGET_SIZE" ]]; then
                    tmux display-message "Pane already docked ($VAL $DIM)"
                    exit 0
                fi

                tmux set-option -p -t "$PANE_ID" @nexus_pre_min_val "$VAL"
                tmux set-option -p -t "$PANE_ID" @nexus_min_dim "$DIM"
                tmux set-option -p -t "$PANE_ID" @nexus_minimized 1
                
                tmux resize-pane -t "$PANE_ID" -"$DIM" "$TARGET_SIZE"
            fi
            tmux display-message "DOCKED: $PANE_ID"
        fi
        ;;
    
    *)
        echo "Usage: nxs-dock toggle"
        exit 1
        ;;
esac
