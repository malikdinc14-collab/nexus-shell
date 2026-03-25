#!/usr/bin/env zsh
# --- Nexus Shell Hooks (Zsh Wrapper) ---
# Sourced in ~/.zshrc via .nexus-shell.zsh

# 1. Source the Shell-Agnostic Core
if [[ -f "${0:h}/shell_hooks.sh" ]]; then
    source "${0:h}/shell_hooks.sh"
elif [[ -n "$NEXUS_HOME" && -f "$NEXUS_HOME/core/kernel/boot/shell_hooks.sh" ]]; then
    source "$NEXUS_HOME/core/kernel/boot/shell_hooks.sh"
fi

# 2. Zsh-Specific Enhancements (Interactive only)
if [[ -o interactive ]]; then
    # Zsh handles directory tracking via add-zsh-hook in shell_hooks.sh
    # This file can be used for further zsh-only features like completions.
    :
fi
