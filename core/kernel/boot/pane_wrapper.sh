#!/bin/bash
# core/kernel/boot/pane_wrapper.sh
# --- Nexus Pane Wrapper ---
# Indestructible viewports: runs a command and falls back to shell on exit.

# 1. Zero-Entropy Path Resolution
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_SCRIPTS="$SCRIPT_DIR"
export ZDOTDIR="$NEXUS_HOME/config/zsh"

# 2. Process Containment: Cleanup children on exit
trap 'pkill -P $$ 2>/dev/null; exit 0' SIGTERM SIGHUP SIGINT

COMMAND="$@"

# Axiom: Explicit Feedback (Negative Space)
if [[ -n "$COMMAND" ]]; then
    printf "\033[1;36m[Axiom] Launching Resource:\033[0m %s\n" "$COMMAND"
    
    # Check for empty variables (Common failure mode)
    if [[ "$COMMAND" == *" $"* || "$COMMAND" == "$"* ]]; then
        printf "\033[1;33m[WARNING] Command contains unexpanded variables. Environment may be sterile.\033[0m\n"
    fi

    # Axiom TTY-01: TUI applications require an attached terminal.
    # During boot, panes are created detached. Give the client 1s to attach
    # before launching TUI-class tools (OpenCode, Yazi, Neovim, etc.)
    case "$1" in
        opencode|yazi|nvim|vim|*opencode*) sleep 1 ;;
    esac

    # Attempt execution with status capture
    eval "$COMMAND"
    EXIT_CODE=$?

    if [[ $EXIT_CODE -ne 0 ]]; then
        printf "\033[1;31m[CRITICAL] Resource terminated with exit code %d.\033[0m\n" "$EXIT_CODE"
    else
        printf "\033[1;32m[SUCCESS] Resource finished gracefully.\033[0m\n"
    fi
else
    printf "\033[1;35m[Axiom] No command provided. Dropping to sterile shell.\033[0m\n"
fi

# Tool exited — drop to an interactive shell so the pane stays alive
printf "\033[1;34m[Nexus] Dropping to interactive containment...\033[0m\n\n"
exec /bin/zsh -i
