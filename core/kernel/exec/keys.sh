#!/bin/bash
# core/kernel/exec/keys.sh
# Live Switcher for Nexus Keybind Profiles

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
KEYBINDS_DIR="$NEXUS_HOME/config/keybinds"
ACTIVE_CONF="$KEYBINDS_DIR/active.conf"

PROFILE="${1}"

# ANSI Colors
CYAN='\033[1;36m'
NC='\033[0m'

list_profiles() {
    ls "$KEYBINDS_DIR"/*.conf | grep -v "active.conf" | xargs -n1 basename | sed 's/\.conf//'
}

apply_profile() {
    local name="$1"
    local file="$KEYBINDS_DIR/${name}.conf"

    if [[ ! -f "$file" ]]; then
        echo "[!] Profile not found: $name"
        return 1
    fi

    echo -e "${CYAN}[*] Applying Keybind Profile: $name...${NC}"
    
    # Update symlink
    ln -sf "$file" "$ACTIVE_CONF"
    
    # Unbind all existing bindings (optional but safer to avoid ghosts)
    # We don't do a full unbind-all to avoid killing core tmux binds,
    # but the source-file will override the ones in default/vim/minimal.
    
    # Reload tmux config
    tmux source-file "$ACTIVE_CONF"
    
    tmux display-message "Keybind Profile: $name applied."
}

show_menu() {
    local selection=$(list_profiles | fzf --ansi --layout=reverse --border=rounded \
        --header="⌨️ Select Keybind Profile" \
        --prompt="Profile > ")

    if [[ -n "$selection" ]]; then
        apply_profile "$selection"
    fi
}

case "$PROFILE" in
    "")      show_menu ;;
    "list")  list_profiles ;;
    *)       apply_profile "$PROFILE" ;;
esac
