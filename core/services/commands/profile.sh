#!/usr/bin/env bash
# core/services/commands/profile.sh
# Entry point for the :profile command.

case "$1" in
    load|*) "${NEXUS_HOME}/core/engine/env/profile_loader.sh" load "$1" ;;
esac
