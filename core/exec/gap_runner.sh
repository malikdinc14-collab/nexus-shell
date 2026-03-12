#!/usr/bin/env bash
# core/exec/gap_runner.sh
# The Autonomous Orchestrator: Bridges GAP approvals to Agent Zero execution.

# Ensure we have the environment
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
GAP_TASKS="$PROJECT_ROOT/.gap/specs/tasks"
STATE_ENGINE="${NEXUS_CORE}/state/state_engine.sh"

echo -e "\033[1;36m[*] INITIALIZING AUTONOMOUS MISSION...\033[0m"

# 1. Validation: Ensure the plan exists
if [[ ! -f "$GAP_TASKS" ]]; then
    echo -e "\033[1;31m[!] Error: No approved GAP tasks found at $GAP_TASKS\033[0m"
    echo "    Please run 'gap scribe create tasks' and 'gap gate approve' first."
    exit 1
fi

# 2. Transition Station to Observability Mode
echo "[*] Switching to Agent-Stream profile..."
# Set the active composition in the state
"$STATE_ENGINE" set ui.active_composition "agent-stream"

# Enable Follow Mode for the bridge
export NEXUS_FOLLOW_MODE=true
export NEXUS_AUTONOMOUS_MODE=true

# Trigger the composition reload in tmux (if active)
if [[ -n "$TMUX" ]]; then
    # We use nxs-profile or similar if available, otherwise force layout engine
    "${NEXUS_CORE}/layout/layout_engine.sh" "$(tmux display-message -p '#S:#I')" "agent-stream"
fi

# 3. Launch Agent Zero (Orbstack Sandbox)
# Based on project architecture, we trigger the agent0 entry point.
# We pass the content of the tasks as the mission goal.
MISSION_GOAL=$(cat "$GAP_TASKS" | head -n 20) # Take the first few lines as context

echo -e "\033[1;32m[*] LAUNCHING AGENT ZERO SANDBOX...\033[0m"

# We assume agent0 is available in the path or via its project root
# Using the standard agent0 launch protocol (simulated based on knowledge)
# In a real environment, this might be: docker compose up or python agent.py
AGENT0_DIR="/Users/Shared/Projects/external_repos/agent0"
if [[ -d "$AGENT0_DIR" ]]; then
    # Run in background so the stream monitor can take over the pane
    (cd "$AGENT0_DIR" && python3 main.py --mission "$MISSION_GOAL" --sandbox orbstack) &
else
    echo "[!] Warning: Agent Zero directory not found. Simulation Mode."
fi

echo "------------------------------------------------"
echo "Mission Dispatched. Watch the Agent-Stream pane."
