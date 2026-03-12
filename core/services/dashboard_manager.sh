#!/bin/bash
# core/services/dashboard_manager.sh
# Multi-modal dashboard service for Nexus Shell

MODE="$1" # ascent | sovereign

case "$MODE" in
    "ascent")
        # ASCENT DASHBOARD
        # This will pipe the actual ascent engine output into a clean TUI
        PROJECT_DIR="/Users/Shared/Projects/school"
        if [[ -d "$PROJECT_DIR" ]]; then
            cd "$PROJECT_DIR"
            # Loop for live monitoring
            while true; do
                clear
                echo -e "\033[1;34m=== ASCENT LEARNER STATE ===\033[0m"
                python3 engine/cli/status.py 2>/dev/null || echo "Ascent engine idle..."
                echo -e "\n\033[1;32m[Recent Evidence]\033[0m"
                ls -rt runs/ | tail -n 5
                sleep 10
            done
        else
            echo "Ascent project not found."
        fi
        ;;
    "sovereign")
        # SOVEREIGN MONITOR
        # Live telemetry for model hosting and memory
        SOV_DIR="/Users/Shared/Projects/sovereign-inference"
        if [[ -d "$SOV_DIR" ]]; then
            while true; do
                clear
                echo -e "\033[1;35m=== SOVEREIGN INFERENCE MONITOR ===\033[0m"
                # Check for active model
                ACTIVE_MODEL=$(nxs-state get project.active_model 2>/dev/null)
                echo "Active Model: ${ACTIVE_MODEL:-None}"
                
                echo -e "\n\033[1;33m[Resource Telemetry]\033[0m"
                # If we had a 'sov status' or similar, we'd use it here
                # For now, let's show memory and CPU for pyproc
                pgrep -f "sov host" | xargs ps -o pid,pcpu,rss,comm -p 2>/dev/null || echo "No active hosting."
                
                echo -e "\n\033[1;36m[Registry Stats]\033[0m"
                jq '. | length' "$SOV_DIR/core/data/registry.json" | xargs -I {} echo "Registered Models: {}"
                
                sleep 5
            done
        else
            echo "Sovereign Inference project not found."
        fi
        ;;
    *)
        echo "Usage: $0 [ascent|sovereign]"
        ;;
esac
