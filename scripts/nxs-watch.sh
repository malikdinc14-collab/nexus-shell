#!/bin/bash

# --- Nexus Control Dashboard ---
# Real-time observability of station health

PANIC_THRESHOLD=15

while true; do
    clear
    echo -e "\033[1;36m[ NEXUS STATION WATCHER ]\033[0m"
    echo "────────────────────────────────────────"
    
    # 1. Process Counts
    N_PANE=$(pgrep -f "pane_wrapper.sh" | wc -l | xargs)
    N_ZOMBIE=$(pgrep -f "sleep 3.0" | wc -l | xargs)
    N_TOTAL=$((N_PANE + N_ZOMBIE))
    
    # Panic Highlighting
    if [ "$N_TOTAL" -gt "$PANIC_THRESHOLD" ]; then
        COLOR="\033[1;31m" # Red
    else
        COLOR="\033[1;32m" # Green
    fi
    
    echo -e "Active Panes:   $N_PANE"
    echo -e "Watchers:       $N_ZOMBIE"
    echo -e "Total Density:  $COLOR$N_TOTAL\033[0m (Limit: $PANIC_THRESHOLD)"
    echo ""
    
    # 2. TMUX Server Status
    if tmux info &>/dev/null; then
        echo -e "TMUX Server:    \033[1;32mONLINE\033[0m"
        tmux list-sessions
    else
        echo -e "TMUX Server:    \033[1;31mOFFLINE\033[0m"
    fi
    echo ""
    
    # 3. Recent Logs
    echo "Recent Logs:"
    tail -n 5 /tmp/nexus_station.log 2>/dev/null || echo "(No logs yet)"
    
    echo -e "\n\033[1;33mCommands: [nxxx] to kill, [Ctrl+C] to stop watcher\033[0m"
    
    sleep 1
done
