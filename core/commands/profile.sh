#!/usr/bin/env bash
# core/commands/profile.sh
# Entry point for the :profile command.

case "$1" in
    load|*) "${NEXUS_HOME}/core/env/profile_loader.sh" load "$1" ;;
esac
