#!/bin/bash
# Load keybindings based on preset or custom config
# Called by tmux config to set up keybindings

NEXUS_CONFIG="${NEXUS_CONFIG:-$HOME/.config/nexus-shell}"
KEYBINDS_CONF="$NEXUS_CONFIG/keybinds.conf"

# Default preset
PRESET="vscode"

# Load user config if exists
if [[ -f "$KEYBINDS_CONF" ]]; then
    source "$KEYBINDS_CONF"
    PRESET="${NEXUS_KEYBIND_PRESET:-vscode}"
fi

# Scripts directory
SCRIPTS="$NEXUS_CONFIG/scripts"

# Define presets
case "$PRESET" in
    vscode)
        KEY_TREE="M-1"
        KEY_EDITOR="M-2"
        KEY_TERMINAL="M-3"
        KEY_CHAT="M-4"
        KEY_SWAP="C-Space"
        KEY_COMMAND='C-\'
        ;;
    mnemonic)
        KEY_TREE="M-n"
        KEY_EDITOR="M-e"
        KEY_TERMINAL="M-t"
        KEY_CHAT="M-c"
        KEY_SWAP="C-Space"
        KEY_COMMAND='C-\'
        ;;
    directional)
        KEY_LEFT="C-h"
        KEY_RIGHT="C-l"
        KEY_DOWN="C-j"
        KEY_UP="C-k"
        KEY_SWAP="C-Space"
        KEY_COMMAND='C-\'
        ;;
    custom)
        KEY_TREE="${NEXUS_KEY_TREE:-M-1}"
        KEY_EDITOR="${NEXUS_KEY_EDITOR:-M-2}"
        KEY_TERMINAL="${NEXUS_KEY_TERMINAL:-M-3}"
        KEY_CHAT="${NEXUS_KEY_CHAT:-M-4}"
        KEY_SWAP="${NEXUS_KEY_SWAP:-C-Space}"
        KEY_COMMAND="${NEXUS_KEY_COMMAND:-C-\\}"
        ;;
esac

# Output tmux commands to bind keys
# These will be eval'd by tmux

if [[ "$PRESET" == "directional" ]]; then
    # Directional style - use select-pane with directions
    cat << EOF
bind-key -n $KEY_LEFT select-pane -L
bind-key -n $KEY_RIGHT select-pane -R
bind-key -n $KEY_DOWN select-pane -D
bind-key -n $KEY_UP select-pane -U
EOF
else
    # Named pane style (vscode, mnemonic, custom)
    cat << EOF
bind-key -n $KEY_TREE select-pane -t :.0
bind-key -n $KEY_EDITOR select-pane -t :.1
bind-key -n $KEY_TERMINAL select-pane -t :.2
bind-key -n $KEY_CHAT if-shell "tmux list-panes -F '#{pane_title}' | grep -q chat" "select-pane -t :.3" ""
EOF
fi

# Common bindings
cat << EOF
bind-key -n $KEY_SWAP run-shell "$SCRIPTS/swap.sh"
bind-key -n $KEY_COMMAND command-prompt -p ":" "run-shell '$SCRIPTS/dispatch.sh %%'"
EOF
