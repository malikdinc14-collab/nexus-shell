#!/bin/bash
# core/kernel/boot/pane_wrapper.sh
# --- Nexus Pane Wrapper ---
# Indestructible viewports: runs a command and falls back to shell on exit.

# 1. Zero-Entropy Path Resolution
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
export NEXUS_SCRIPTS="$SCRIPT_DIR"
export ZDOTDIR="$NEXUS_HOME/config/zsh"

# 2. Process Containment: Cleanup children on exit
trap 'pkill -P $$ 2>/dev/null; exit 0' SIGTERM SIGHUP SIGINT

COMMAND="$@"

# ── Negative Space: Assert invariants before execution ──
if [[ -z "$NEXUS_HOME" || ! -d "$NEXUS_HOME" ]]; then
    printf "\033[1;31m[INVARIANT] NEXUS_HOME not set or missing: '%s'\033[0m\n" "$NEXUS_HOME"
fi

if [[ -n "$COMMAND" ]]; then
    # Extract the binary from the command (first word, strip quotes)
    CMD_BIN=$(echo "$COMMAND" | sed "s/^'//;s/'$//" | awk '{print $1}')
    # Resolve $VAR-style references
    CMD_BIN=$(eval echo "$CMD_BIN" 2>/dev/null)
    if [[ -n "$CMD_BIN" && "$CMD_BIN" != /* ]] && ! command -v "$CMD_BIN" &>/dev/null; then
        printf "\033[1;31m[INVARIANT] Command binary not found: '%s'\033[0m\n" "$CMD_BIN"
        printf "\033[1;33m  Full command: %s\033[0m\n" "$COMMAND"
        printf "\033[1;33m  PATH: %s\033[0m\n" "$PATH"
    elif [[ -n "$CMD_BIN" && "$CMD_BIN" == /* && ! -x "$CMD_BIN" ]]; then
        printf "\033[1;31m[INVARIANT] Command not executable: '%s'\033[0m\n" "$CMD_BIN"
        ls -la "$CMD_BIN" 2>/dev/null
    fi

    eval "$COMMAND"
    EXIT_CODE=$?

    if [[ $EXIT_CODE -ne 0 ]]; then
        printf "\033[1;31m[INVARIANT] Process exited non-zero: code=%d cmd='%s'\033[0m\n" "$EXIT_CODE" "$COMMAND"
    fi
fi

# Tool exited — drop to an interactive shell so the pane stays alive
FALLBACK_SHELL="$(command -v zsh 2>/dev/null || command -v bash 2>/dev/null || echo /bin/sh)"
exec "$FALLBACK_SHELL" -i
