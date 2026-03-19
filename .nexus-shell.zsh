# --- Nexus-Shell Identity Firewall ---

# 1. Global Entry Point
alias nxs="${NEXUS_HOME:-$HOME/.config/nexus-shell}/core/kernel/boot/launcher.sh"
alias nexus="${NEXUS_HOME:-$HOME/.config/nexus-shell}/core/kernel/boot/launcher.sh"

# 2. Contextual Activation Invariant
if [[ "$TMUX" == *"nexus_"* ]]; then
    export NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
    export NEXUS_CONFIG="$NEXUS_HOME"
    export NEXUS_BIN="${NEXUS_BIN:-$HOME/.nexus-shell/bin}"
    export NEXUS_STATION_ACTIVE=1
    
    # Prepend tools to PATH locally
    export PATH="$NEXUS_BIN:$PATH"
    
    # Enable sync hooks (Universal POSIX fallback)
    if [[ -f "$NEXUS_HOME/core/kernel/boot/shell_hooks.sh" ]]; then
        source "$NEXUS_HOME/core/kernel/boot/shell_hooks.sh"
    elif [[ -f "$NEXUS_HOME/core/kernel/boot/shell_hooks.zsh" ]]; then
        # Backwards compatibility for zsh-only setups
        source "$NEXUS_HOME/core/kernel/boot/shell_hooks.zsh"
    fi
fi
