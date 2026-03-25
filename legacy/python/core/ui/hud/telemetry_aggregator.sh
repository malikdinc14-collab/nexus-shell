#!/usr/bin/env bash
# core/ui/hud/telemetry_aggregator.sh
# Aggregates system, workspace, and agent state into a single JSON file.

TELEMETRY_FILE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}/telemetry.json"

# Atomic mktemp helper
safe_mktemp() {
    local tmp_dir="/tmp/nexus_$(whoami)/${PROJECT_NAME:-global}"
    mkdir -p "$tmp_dir/tmp"
    # Use -t for fallback but favor the explicit path template
    mktemp "$tmp_dir/tmp/telemetry.XXXXXX" 2>/dev/null || mktemp -t "nexus_telemetry"
}

# Initialize file if not exists
if [ ! -f "$TELEMETRY_FILE" ]; then
    echo '{"agent":{"status":"idle","mission":""},"env":{"workspace":"none","profile":"default","locality":"local"}}' > "$TELEMETRY_FILE"
fi

update_telemetry() {
    local key=$1
    local value=$2
    # Simple jq update
    local temp_file=$(safe_mktemp)
    jq "$key = \"$value\"" "$TELEMETRY_FILE" > "$temp_file" && mv "$temp_file" "$TELEMETRY_FILE"
}

# Main loop
while true; do
    # 1. Update Core Telemetry
    workspace_name=${NEXUS_WORKSPACE_NAME:-"no-workspace"}
    profile_name=${NEXUS_PROFILE:-"standard"}
    locality="local"
    if [[ $(hostname) == *"m1"* ]]; then locality="m1-local"; elif [[ $(hostname) == *"m4"* ]]; then locality="m4-remote"; fi
    
    git_branch="none"
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git_branch=$(git rev-parse --abbrev-ref HEAD)
    fi

    # 2. Collect Module Telemetry
    # This is the new modular core
    modules_json="{}"
    if [ -d "core/ui/hud/modules" ]; then
        for mod in core/ui/hud/modules/*.sh; do
            if [ -f "$mod" ] && [ -x "$mod" ]; then
                mod_name=$(basename "$mod" .sh)
                mod_data=$("$mod" --json 2>/dev/null)
                if [[ -n "$mod_data" ]]; then
                    # Validate JSON before passing to jq --argjson
                    if echo "$mod_data" | jq -e . >/dev/null 2>&1; then
                        modules_json=$(echo "$modules_json" | jq --arg name "$mod_name" --argjson data "$mod_data" '. + {($name): $data}')
                    else
                        # Log error to a file instead of spamming stderr (often current terminal)
                        LOCAL_LOG="/tmp/nexus_aggregator.log"
                        echo "[$(date +%T)] Warning: HUD module $mod_name returned invalid JSON: $mod_data" >> "$LOCAL_LOG"
                    fi
                fi
            fi
        done
    fi

    # 3. Write Atomic Update
    TEMP_OUT=$(safe_mktemp)
    jq -n \
        --arg win "$workspace_name" \
        --arg prof "$profile_name" \
        --arg loc "$locality" \
        --arg branch "$git_branch" \
        --argjson mods "$modules_json" \
        '{
            env: {workspace: $win, profile: $prof, locality: $loc, git_branch: $branch},
            modules: $mods,
            updated_at: (now | strftime("%H:%M:%S"))
        }' > "$TEMP_OUT" 2>/dev/null && mv "$TEMP_OUT" "$TELEMETRY_FILE" 2>/dev/null || { [[ -n "$TEMP_OUT" ]] && rm -f "$TEMP_OUT" 2>/dev/null; }

    sleep 1
done
