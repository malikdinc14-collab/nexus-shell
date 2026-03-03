#!/bin/bash
# Generic Module Installer Template
# Usage: ./install.sh [bin_dir] [os] [arch]

BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

echo "    Installing [MODULE_NAME]..."

# 1. Check if already installed
if [[ -x "$BIN_DIR/[BINARY_NAME]" ]]; then
    echo "    [MODULE_NAME] already installed."
    exit 0
fi

# 2. Download logic (replace with specific logic)
# curl -L ...

# 3. Config setup (optional)
# cp config/* ...

echo "    [MODULE_NAME] installed successfully."
