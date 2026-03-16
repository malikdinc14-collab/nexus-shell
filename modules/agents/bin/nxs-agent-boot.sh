#!/usr/bin/env bash
# modules/agents/bin/nxs-agent-boot.sh
# Universal AI Agent Dispatcher for Nexus Shell.
#
# Reads .nexus/agents/default.yaml and spawns the configured AI backend.
# Handles Keychain API key injection, context management, and GAP alignment mode.

set -e

# ── Paths ────────────────────────────────────────────────────────────────────
NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
KEYS_BIN="${NEXUS_HOME}/bin/nxs-keys.sh"
AGENT_CONF_PATH="${PROJECT_ROOT}/.nexus/agents/default.yaml"

if [[ ! -f "$AGENT_CONF_PATH" ]]; then
    # Fallback to general project config
    AGENT_CONF_PATH="${NEXUS_HOME}/.nexus/agents/default.yaml"
fi

if [[ ! -f "$AGENT_CONF_PATH" ]]; then
    echo "[Nexus] Error: No agent configuration found at $AGENT_CONF_PATH"
    exit 1
fi

# ── Helper: Read YAML via Python ─────────────────────────────────────────────
get_conf() {
    python3 -c "import yaml; print(yaml.safe_load(open('$AGENT_CONF_PATH')).get('$1', '$2'))" 2>/dev/null || echo "$2"
}

# ── Load Config ─────────────────────────────────────────────────────────────
BACKEND=$(get_conf "backend" "claude-code")
MODEL=$(get_conf "model" "anthropic/claude-sonnet-4")
API_BASE=$(get_conf "api_base" "http://localhost:8080/v1")
CONTEXT=$(get_conf "context" "null")
RAG=$(get_conf "rag" "null")
GAP_SESSION=$(get_conf "gap_session" "false")

# ── API Key Injection ────────────────────────────────────────────────────────
# Export keys for LiteLLM backends
eval "$($KEYS_BIN export anthropic 2>/dev/null || true)"
eval "$($KEYS_BIN export openai 2>/dev/null || true)"
eval "$($KEYS_BIN export google 2>/dev/null || true)"
eval "$($KEYS_BIN export deepseek 2>/dev/null || true)"
eval "$($KEYS_BIN export openrouter 2>/dev/null || true)"

# ── Context & Skills ──────────────────────────────────────────────────────────
EXTRA_FLAGS=()

# Load superpowers if configured
if [[ "$CONTEXT" == "superpowers" ]]; then
    SP_SKILLS="${NEXUS_HOME}/external/superpowers/skills"
    if [[ -d "$SP_SKILLS" ]]; then
        if [[ "$BACKEND" == "claude-code" ]]; then
            # Claude Code uses .claude-plugin hooks
            echo "[Nexus] Loading Superpowers skills..."
        fi
    fi
fi

# ── RAG Integration ───────────────────────────────────────────────────────────
if [[ "$RAG" == "openviking" ]]; then
    echo "[Nexus] RAG Enabled: OpenViking"
    # Placeholder for OpenViking context injection
fi

# ── GAP Alignment Logic ───────────────────────────────────────────────────────
# Detect project-level manifest
GAP_MANIFEST="${PROJECT_ROOT}/manifest.yaml"
if [[ ! -f "$GAP_MANIFEST" ]]; then
    GAP_MANIFEST="${PROJECT_ROOT}/.gap/manifest.yaml"
fi

# ── Execution ─────────────────────────────────────────────────────────────────
echo "[Nexus] Booting $BACKEND [$MODEL]"

# Helper for GAP wrapping
run_agent() {
    local backend=$1
    shift
    if [[ "$GAP_SESSION" == "true" ]]; then
        # Use 'gap agent' for alignment sessions
        exec gap agent "$backend" --manifest "$GAP_MANIFEST" --args "$*"
    else
        # Normal execution
        exec "$backend" "$@"
    fi
}

case "$BACKEND" in
    claude-code)
        export ANTHROPIC_BASE_URL="$API_BASE"
        run_agent "claude" --model "$MODEL" "${EXTRA_FLAGS[@]}"
        ;;
    pi)
        export OPENAI_BASE_URL="$API_BASE"
        run_agent "pi" --model "$MODEL" "${EXTRA_FLAGS[@]}"
        ;;
    *)
        run_agent "$BACKEND" --model "$MODEL" "${EXTRA_FLAGS[@]}"
        ;;
esac
