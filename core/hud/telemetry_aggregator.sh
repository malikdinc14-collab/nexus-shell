#!/usr/bin/env bash
# core/hud/telemetry_aggregator.sh
# Aggregates system, workspace, and agent state into a single JSON file.

TELEMETRY_FILE="/tmp/nexus_telemetry.json"

# Initialize file if not exists
if [ ! -f "$TELEMETRY_FILE" ]; then
    echo '{"agent":{"status":"idle","mission":""},"env":{"workspace":"none","profile":"default","locality":"local"}}' > "$TELEMETRY_FILE"
fi

update_telemetry() {
    local key=$1
    local value=$2
    # Simple jq update
    local temp_file=$(mktemp)
    jq "$key = \"$value\"" "$TELEMETRY_FILE" > "$temp_file" && mv "$temp_file" "$TELEMETRY_FILE"
}

# Main loop (could be run as a daemon)
while true; do
    # 1. Detect active workspace (from global env if set, otherwise fallback)
    workspace_name=${NEXUS_WORKSPACE_NAME:-"no-workspace"}
    update_telemetry ".env.workspace" "$workspace_name"

    # 2. Detect active profile
    profile_name=${NEXUS_PROFILE:-"standard"}
    update_telemetry ".env.profile" "$profile_name"

    # 3. Detect locality (check if we are on M1/M4)
    # Simple heuristic for now
    locality="m1-local"
    if [[ $(hostname) == *"m4"* ]]; then locality="m4-remote"; fi
    update_telemetry ".env.locality" "$locality"

    # 4. Detect Git Branch
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git_branch=$(git rev-parse --abbrev-ref HEAD)
    else
        git_branch="none"
    fi
    update_telemetry ".env.git_branch" "$git_branch"

    sleep 1
done
