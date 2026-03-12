#!/bin/bash
# core/services/nxs-stream.sh
# Universal Stream Monitor for Nexus Shell (multiplexing thoughts/tools)

LOG_FILE="/tmp/agent0_sandbox_stream.log"
CATEGORY=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --category) CATEGORY="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

clear
echo -e "\033[1;36m=== 🕵️ NEXUS STREAM: ${CATEGORY:-GENERAL} ===\033[0m"
echo -e "\033[1;30mWatching: $LOG_FILE\033[0m"
echo "--------------------------------"

if [[ ! -f "$LOG_FILE" ]]; then
    touch "$LOG_FILE"
fi

# Streaming logic with AWK filtering
tail -f "$LOG_FILE" | awk -v cat="$CATEGORY" '
    # If category is set, filter by it
    cat != "" && !($0 ~ "\\[" cat "\\]") { next }

    /\[THOUGHT\]/ { sub(/.*\[THOUGHT\] >> /, ""); print "\033[1;34m💭 " $0 "\033[0m"; next }
    /\[TOOL\]/ { sub(/.*\[TOOL\] >> /, ""); print "\033[1;33m🛠️  " $0 "\033[0m"; next }
    /\[INFO\]/ { sub(/.*\[INFO\] >> /, ""); print "\033[0;37mℹ️  " $0 "\033[0m"; next }
    /\[ERROR\]/ { sub(/.*\[ERROR\] >> /, ""); print "\033[1;31m🚨 " $0 "\033[0m"; next }
    /\[DIFF\]/ { sub(/.*\[DIFF\] >> /, ""); print "\033[1;36m📝 DIFF: " $0 "\033[0m"; next }
    /^[+-]/ { 
        if ($0 ~ /^\+/) print "\033[0;32m" $0 "\033[0m"
        else if ($0 ~ /^-/) print "\033[0;31m" $0 "\033[0m"
        next 
    }
    
    # Default fallback for untagged lines
    cat == "" && !/\[(TASK|THOUGHT|TOOL|INFO|ERROR|SIGNAL|DIFF)\]/ { print "\033[0;90m" $0 "\033[0m" }
'
