#!/usr/bin/env bash
# core/commands/workspace.sh
# Entry point for the :workspace command.

case "$1" in
    load) "${NEXUS_HOME}/core/workspace/workspace_manager.sh" load "$2" ;;
    *) echo "Usage: :workspace load <path>" ;;
esac
