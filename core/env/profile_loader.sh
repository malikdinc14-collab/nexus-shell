#!/usr/bin/env bash
# core/env/profile_loader.sh
# Loads role-based environment settings from YAML profiles.

load_profile() {
    local profile_name="$1"
    local profile_file="${NEXUS_HOME}/config/profiles/${profile_name}.yaml"

    if [[ ! -f "$profile_file" ]]; then
        echo "[!] Error: Profile not found: $profile_name"
        return 1
    fi

    echo "[*] Activating Profile: $profile_name"

    # 1. Extract and apply theme
    local theme=$(yq -r '.theme // empty' "$profile_file")
    if [[ -n "$theme" ]]; then
        "$NEXUS_HOME/core/boot/theme.sh" apply "$theme"
    fi

    # 2. Extract and apply composition
    local composition=$(yq -r '.composition // empty' "$profile_file")
    if [[ -n "$composition" ]]; then
        # Trigger layout swap
        nexus-switch-layout "$composition"
    fi

    # 3. Set environment variables
    eval "$(yq -r '.env // empty | to_entries | .[] | "export " + .key + "=\"" + .value + "\""' "$profile_file")"
    
    # 4. Update HUD
    export NEXUS_PROFILE="$profile_name"
    # The telemetry aggregator will pick this up
}

case "$1" in
    load) load_profile "$2" ;;
    *) echo "Usage: $0 load <name>" ;;
esac
