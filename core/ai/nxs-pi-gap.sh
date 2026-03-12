#!/bin/bash
# core/ai/nxs-pi-gap.sh
# Bridges the GAP mission context to the Pi AI agent.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
GAP_DIR="$NEXUS_HOME/.gap"
PI_MONO_DIR="$NEXUS_HOME/external/pi-mono"

# 1. Discover Active Mission or File
# If a file is passed, we include it in the briefing.
TARGET="${1}"
FILE_CONTEXT=""

if [[ -f "$TARGET" ]]; then
    FILE_CONTEXT="\n\n## ATTACHED FILE: $(basename "$TARGET")\n$(cat "$TARGET" | head -n 100)\n"
    MISSION_ID=$(ls -td "$GAP_DIR/features"/*/ 2>/dev/null | head -1 | xargs basename)
else
    MISSION_ID="$TARGET"
    [[ -z "$MISSION_ID" ]] && MISSION_ID=$(ls -td "$GAP_DIR/features"/*/ 2>/dev/null | head -1 | xargs basename)
fi

if [[ -z "$MISSION_ID" ]]; then
    # Even if no mission, we can still chat with the file context
    MISSION_ID="General Chat"
    FEATURE_DIR=""
else
    FEATURE_DIR="$GAP_DIR/features/$MISSION_ID"
fi

STATUS_FILE="$FEATURE_DIR/status.yaml"

# 2. Extract Mission Briefing
echo "[Nexus] Compiling GAP Mission Briefing: $MISSION_ID" >&2

BRIEFING="# MISSION BRIEFING: $MISSION_ID\n\n"

if [[ -f "$STATUS_FILE" ]]; then
    PHASE=$(grep "status:" "$STATUS_FILE" | cut -d' ' -f2)
    BRIEFING="${BRIEFING}## CURRENT LEDGER PHASE: $PHASE\n\n"
fi

if [[ -f "$FEATURE_DIR/requirements.md" ]]; then
    BRIEFING="${BRIEFING}## Requirements\n$(cat "$FEATURE_DIR/requirements.md" | head -n 30)\n\n"
fi

if [[ -f "$FEATURE_DIR/design.md" ]]; then
    BRIEFING="${BRIEFING}## Design Constraints\n$(cat "$FEATURE_DIR/design.md" | head -n 30)\n\n"
fi

if [[ -f "$FEATURE_DIR/tasks.md" ]]; then
    BRIEFING="${BRIEFING}## Active Tasks\n$(grep "\[ \]" "$FEATURE_DIR/tasks.md" | head -n 10)\n\n"
fi

    # Add Specialist Division (Nexus Hub)
    # This allows Pi to use 142 specialized agents from agency-agents
    if [[ -d "$NEXUS_HOME/external/agency-agents" ]]; then
        export PI_SYSTEM_MESSAGE="${PI_SYSTEM_MESSAGE}

SPECIALIST DIVISION:
You have access to 142 specialized agency-agents personalities. Use them for cross-domain validation."
        export AGENCY_AGENTS_PATH="$NEXUS_HOME/external/agency-agents"
    fi

# 3. External Superpowers Integration
EXTERNAL_REPOS="$NEXUS_HOME/external"
EXTRA_FLAGS=(
    --skill "$EXTERNAL_REPOS/superpowers/skills"
    --skill "$EXTERNAL_REPOS/hve-core/.github/skills"
    --prompt-template "$EXTERNAL_REPOS/hve-core/.github/prompts"
)

# 4. Inject into Pi Environment
# We use the --system-prompt flag to start Pi with this context
export PI_SYSTEM_MESSAGE="$BRIEFING$FILE_CONTEXT\n\nIMPORTANT: You are acting as a GAP-aligned agent. You MUST respect the current LEDGER status and only perform actions within the approved scope.\n\nSUPERPOWERS ENABLED:\n- Use 'skill' tool to access Jesse's Superpowers framework ($EXTERNAL_REPOS/superpowers).\n- Use HVE methodologies (Research-Plan-Implement) from Microsoft's hve-core.\n- Reasoning Optimized: OptiLLM ($EXTERNAL_REPOS/optillm) logic is active.\n- Evolutionary Discovery: OpenEvolve ($EXTERNAL_REPOS/openevolve) is available.\n- Specialist Division: 140+ specialized agents from msitarzewski/agency-agents ($EXTERNAL_REPOS/agency-agents) are available for delegation."

# Launch Pi from the local mono repo with all extra capability flags
# We attach the superpower repos as context so Pi knows how to use them
cd "$PI_MONO_DIR" && npm run start -- "${EXTRA_FLAGS[@]}" --system-prompt "$PI_SYSTEM_MESSAGE" "@$EXTERNAL_REPOS/optillm" "@$EXTERNAL_REPOS/openevolve" "@$EXTERNAL_REPOS/agency-agents"
