#!/usr/bin/env bash
# core/engine/env/profile_loader.sh
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
        "$NEXUS_HOME/core/kernel/boot/theme.sh" apply "$theme"
    fi

    # 2. Extract and apply composition
    local composition=$(yq -r '.composition // empty' "$profile_file")
    if [[ -n "$composition" ]]; then
        # Trigger layout swap
        nexus-switch-layout "$composition"
    fi

    # 3. Set environment variables
    eval "$(yq -r '.env // empty | to_entries | .[] | "export " + .key + "=\"" + .value + "\""' "$profile_file")"
    
    # 4. Extract Tool Stacks and Sync to State Engine
    # Stacks are defined as: tools: { chat: [pi, opencode], editor: [nvim, micro] }
    local STATE_ENGINE="${NEXUS_CORE}/state/state_engine.sh"
    if [[ -x "$STATE_ENGINE" ]]; then
        # Export the full tools JSON to the state engine
        local tools_json=$(yq -c '.tools // empty' "$profile_file")
        if [[ -n "$tools_json" && "$tools_json" != "null" ]]; then
            "$STATE_ENGINE" set ui.stacks "$tools_json"
        fi
        "$STATE_ENGINE" set active_profile "$profile_name"
    fi

    # 5. Launcher specialized HUD Provider if it exists
    local hud_provider=$(yq -r '.hud_provider // empty' "$profile_file")
    if [[ -n "$hud_provider" ]]; then
        # Kill any existing providers first (clean swap)
        pkill -f "hud/.*_provider.sh" 2>/dev/null || true
        # Start the new provider in background
        "${NEXUS_HOME}/${hud_provider}" &
    fi

    # 6. AI Sovereignty: Isolate State and Bootstrap Models
    # Each profile gets its own Pi state directory to prevent session/brain bleed.
    export PI_CODING_AGENT_DIR="${NEXUS_HOME}/.nexus/ai/${profile_name}"
    mkdir -p "$PI_CODING_AGENT_DIR"

    # If the profile defines 'ai_models', we generate the models.json for that profile.
    local ai_models=$(yq -c '.ai_models // empty' "$profile_file")
    if [[ -n "$ai_models" && "$ai_models" != "null" ]]; then
        echo "[*] Bootstrapping AI Models: ${profile_name}"
        echo "$ai_models" > "$PI_CODING_AGENT_DIR/models.json"
    fi

    export NEXUS_PROFILE="$profile_name"
    # The telemetry aggregator will pick this up
}

case "$1" in
    load) load_profile "$2" ;;
    *) echo "Usage: $0 load <name>" ;;
esac
