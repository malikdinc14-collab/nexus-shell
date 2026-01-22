#!/bin/bash

# --- Nexus-Shell Local Installer ---
# Syncs code from this project folder to your live environment (~/.config)

SOURCE_SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/scripts" && pwd)"
SOURCE_TMUX="$(cd "$(dirname "${BASH_SOURCE[0]}")/config/tmux" && pwd)"
INSTALL_SCRIPTS="$HOME/.config/nexus-shell/scripts"
INSTALL_TMUX="$HOME/.config/nexus-shell/tmux"

echo "[*] Installing Nexus-Shell to $HOME/.config/nexus-shell..."

mkdir -p "$INSTALL_SCRIPTS"
mkdir -p "$INSTALL_TMUX"

# Perform the sync
cp -rv "$SOURCE_SCRIPTS/"* "$INSTALL_SCRIPTS/"
cp -rv "$SOURCE_TMUX/"* "$INSTALL_TMUX/"

echo "[*] Success. Your live station has been updated."
