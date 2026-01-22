# --- Nexus-Shell Identity Firewall ---

# 1. Global Entry Point
# These point to the STABLE installation in .config
alias nxs="/Users/compute/.config/nexus-shell/scripts/launcher.sh"
alias nexus="/Users/compute/.config/nexus-shell/scripts/launcher.sh"

# 2. Contextual Activation Invariant
# Variables and tools ONLY activate inside a Nexus TMUX session
if [[ "$TMUX" == *"nexus_"* ]]; then
    export NEXUS_HOME="/Users/compute/.config/nexus-shell"
    export NEXUS_CONFIG="$NEXUS_HOME"
    export NEXUS_BIN="/Users/compute/.nexus-shell/bin"
    export NEXUS_STATION_ACTIVE=1
    
    # Prepend tools to PATH locally
    export PATH="$NEXUS_BIN:$PATH"
    
    # Enable sync hooks (if they exist)
    if [[ -f "$NEXUS_HOME/scripts/shell_hooks.zsh" ]]; then
        source "$NEXUS_HOME/scripts/shell_hooks.zsh"
    fi
fi
