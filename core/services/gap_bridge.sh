#!/usr/bin/env bash
# core/services/gap_bridge.sh
# Bridge to the Gated Agent Protocol (GAP) project.
# Handles environment discovery and command delegation.

# 1. Discovery Logic
# Priority: 
#   A. USER_GAP_PATH env var
#   B. project-local Gated Agent Protocol/src/main.py
#   C. ~/.nexus-shell/tooling/gap/venv/bin/gap

GAP_PROJECT_PATH="/Users/Shared/Projects/Gated Agent Protocol"

if [[ -n "$USER_GAP_PATH" ]]; then
    GAP_CMD="$USER_GAP_PATH"
elif [[ -d "$GAP_PROJECT_PATH" ]]; then
    # Use the shared project path directly if available
    GAP_CMD="python3 '$GAP_PROJECT_PATH/src/gap/main.py'"
elif [[ -f "$HOME/.nexus-shell/tooling/gap/venv/bin/gap" ]]; then
    GAP_CMD="$HOME/.nexus-shell/tooling/gap/venv/bin/gap"
else
    # Fallback to system-wide if any
    GAP_CMD="gap"
fi

# 2. Delegation
case "$1" in
    run|execute)
        shift
        "${NEXUS_HOME}/core/exec/gap_runner.sh" "$@"
        ;;
    *)
        # Wrap the call in a submodule execution if it's a python script
        if [[ "$GAP_CMD" == *"python3"* ]]; then
            eval "$GAP_CMD $@"
        else
            $GAP_CMD "$@"
        fi
        ;;
esac
