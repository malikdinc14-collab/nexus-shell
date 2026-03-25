#!/usr/bin/env zsh
# core/kernel/exec/guard.sh
# The Nexus Safety Airlock. Intercepts and gates destructive shell commands.

CONFIG_FILE="${NEXUS_HOME}/config/safety.yaml"
# Use project-local storage for permissions to support project-specific whitelisting
PERMISSIONS_FILE="${PROJECT_ROOT}/.nexus/permissions.json"
COMMAND="$*"

# Ensure permissions file exists
mkdir -p "$(dirname "$PERMISSIONS_FILE")"
[[ ! -f "$PERMISSIONS_FILE" ]] && echo '{"session": [], "forever": []}' > "$PERMISSIONS_FILE"

# 1. Load Dangerous Patterns from safety.yaml
# (Simplified YAML parsing for shell)
PATTERNS=($(grep "^  - " "$CONFIG_FILE" | sed "s/^  - //" | sed "s/['\"]//g"))

# 2. Check if command matches any dangerous pattern
IS_DANGEROUS=false
for p in "${PATTERNS[@]}"; do
    if [[ "$COMMAND" =~ $p ]]; then
        IS_DANGEROUS=true
        MATCHED_PATTERN="$p"
        break
    fi
done

if [[ "$IS_DANGEROUS" == "false" ]]; then
    eval "$COMMAND"
    exit $?
fi

# 3. Check for existing permissions (Session/Forever)
# We check if the EXACT command or the PATTERN is whitelisted
PERM_CHECK=$(python3 -c "
import json, os, re
try:
    with open('$PERMISSIONS_FILE', 'r') as f:
        data = json.load(f)
    cmd = '$COMMAND'
    pattern = '$MATCHED_PATTERN'
    if cmd in data['session'] or cmd in data['forever'] or pattern in data['session'] or pattern in data['forever']:
        print('ALLOWED')
    else:
        print('ASK')
except:
    print('ASK')
")

if [[ "$PERM_CHECK" == "ALLOWED" ]]; then
    eval "$COMMAND"
    exit $?
fi

# 4. Prompt the user via tmux popup
# --- SIGNAL HUD: SAFETY BLOCKED ---
TELEMETRY_FILE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}/telemetry.json"
PREV_STATUS=$(jq -r '.agent.status' "$TELEMETRY_FILE" 2>/dev/null || echo "idle")
python3 -c "import json, os; data = json.load(open('$TELEMETRY_FILE')) if os.path.exists('$TELEMETRY_FILE') else {}; data.setdefault('agent', {})['status'] = 'safety_blocked'; data.setdefault('agent', {})['mission'] = 'Decision Required: $MATCHED_PATTERN'; json.dump(data, open('$TELEMETRY_FILE', 'w'))"

echo -e "\033[1;31m[NEXUS GUARD] Destructive command detected!\033[0m"
echo -e "\033[1;33mCommand: $COMMAND\033[0m"
echo -e "\033[1;30mPattern matched: $MATCHED_PATTERN\033[0m"

if [[ -z "$TMUX" ]]; then
    # Fallback to standard prompt if not in tmux
    echo -n "Allow execution? (y/N): "
    read -r choice
    [[ "$choice" == "y" ]] && eval "$COMMAND" && exit $?
    exit 1
fi

# Show tmux menu for permission tiers
CHOICE=$(tmux display-menu -p "Nexus Guard: Destroy Safety Airlock" \
    "Allow Once" "o" "ONCE" \
    "Allow for Session" "s" "SESSION" \
    "Allow Forever" "f" "FOREVER" \
    "Deny" "d" "DENY")

case "$CHOICE" in
    ONCE)
        eval "$COMMAND"
        exit $?
        ;;
    SESSION)
        python3 -c "
import json
with open('$PERMISSIONS_FILE', 'r+') as f:
    data = json.load(f)
    data['session'].append('$COMMAND')
    f.seek(0)
    json.dump(data, f)
    f.truncate()
"
        eval "$COMMAND"
        exit $?
        ;;
    FOREVER)
        python3 -c "
import json
with open('$PERMISSIONS_FILE', 'r+') as f:
    data = json.load(f)
    data['forever'].append('$COMMAND')
    f.seek(0)
    json.dump(data, f)
    f.truncate()
"
        eval "$COMMAND"
        exit $?
        ;;
    *)
        echo -e "\033[1;31m[!] Execution Aborted by User.\033[0m"
        python3 -c "import json, os; data = json.load(open('$TELEMETRY_FILE')) if os.path.exists('$TELEMETRY_FILE') else {}; data.setdefault('agent', {})['status'] = '$PREV_STATUS'; json.dump(data, open('$TELEMETRY_FILE', 'w'))"
        exit 1
        ;;
esac

# Restore Status on Success
python3 -c "import json, os; data = json.load(open('$TELEMETRY_FILE')) if os.path.exists('$TELEMETRY_FILE') else {}; data.setdefault('agent', {})['status'] = '$PREV_STATUS'; json.dump(data, open('$TELEMETRY_FILE', 'w'))"
