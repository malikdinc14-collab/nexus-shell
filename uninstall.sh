#!/bin/bash

# --- Nexus-Shell Uninstaller ---
# Removes nexus-shell configuration for the current user

set -e

USER_HOME="$HOME"
USER_NAME="$(whoami)"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║            NEXUS-SHELL UNINSTALLER                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Uninstalling for user: $USER_NAME"
echo ""

read -p "This will remove all Nexus-Shell symlinks and configs. Continue? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""

# === Remove config symlinks ===
echo "[1/4] Removing configuration symlinks..."

remove_symlink() {
    local target="$1"
    if [[ -L "$target" ]]; then
        rm "$target"
        echo "      Removed: $target"
    fi
}

remove_symlink "$USER_HOME/.config/nvim"
remove_symlink "$USER_HOME/.config/yazi"
remove_symlink "$USER_HOME/.config/opencode"

# === Remove launcher symlinks ===
echo "[2/4] Removing launcher commands..."

remove_symlink "/usr/local/bin/nexus"
remove_symlink "/usr/local/bin/nxs"
remove_symlink "$USER_HOME/bin/nexus"
remove_symlink "$USER_HOME/bin/nxs"

# === Remove shell integration ===
echo "[3/4] Removing shell integration..."

if [[ -f "$USER_HOME/.nexus.zsh" ]]; then
    rm "$USER_HOME/.nexus.zsh"
    echo "      Removed: ~/.nexus.zsh"
fi

# Note: We don't remove the source line from .zshrc to avoid breaking things
echo "      Note: You may want to remove the nexus line from ~/.zshrc manually"

# === Clean state directory ===
echo "[4/4] Cleaning state directory..."

NEXUS_STATE="/tmp/nexus_$USER_NAME"
if [[ -d "$NEXUS_STATE" ]]; then
    rm -rf "$NEXUS_STATE"
    echo "      Removed: $NEXUS_STATE"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            UNINSTALL COMPLETE                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Notes:"
echo "  - The nexus-shell directory itself was NOT removed"
echo "  - Config backups (*.backup.*) were NOT removed"
echo "  - You may want to edit ~/.zshrc to remove the nexus source line"
echo ""
