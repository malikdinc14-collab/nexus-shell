# Nexus-specific .zshrc
# Sources the system default and adds Nexus-Sovereign powerups.

# 1. Source User's Original Shell Config
if [[ -f "$HOME/.zshrc" ]]; then
    source "$HOME/.zshrc"
fi

# 2. Inject Nexus Aliases & Environment
if [[ -f "/Users/Shared/Projects/nexus-shell/core/boot/nxs-aliases.sh" ]]; then
    source "/Users/Shared/Projects/nexus-shell/core/boot/nxs-aliases.sh"
    # echo "   [*] Nexus Sovereign Shell Active."
fi

# 3. Custom Prompt Injection (Optional, but good for context)
# export PS1="%F{cyan}nexus%f %F{blue}%~%f %# "
