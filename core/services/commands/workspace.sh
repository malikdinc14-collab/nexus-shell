#!/usr/bin/env bash
# core/services/commands/workspace.sh
# Entry point for the :workspace command.

case "$1" in
    load) "${NEXUS_HOME}/core/engine/workspace/workspace_manager.sh" load "$2" ;;
    *) echo "Usage: :workspace load <path>" ;;
esac
