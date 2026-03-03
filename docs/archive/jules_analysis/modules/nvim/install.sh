#!/bin/bash
BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

if [[ -x "$BIN_DIR/nvim" ]]; then exit 0; fi

echo "    [nvim] Downloading..."
if [[ "$OS" == "macos" ]]; then
    URL="https://github.com/neovim/neovim/releases/latest/download/nvim-macos-${ARCH}.tar.gz"
    curl -sL "$URL" -o nvim.tar.gz
    tar -xzf nvim.tar.gz
    cp -r nvim-macos-${ARCH}/* "$HOME/.nexus-shell/" 2>/dev/null || cp -r nvim-macos-${ARCH}/* "$HOME/.nexus-shell/"
    rm -rf nvim.tar.gz nvim-macos-${ARCH}
else
    # Linux logic simplified for brevity/parity
    URL="https://github.com/neovim/neovim/releases/latest/download/nvim-linux64.tar.gz"
    curl -sL "$URL" -o nvim.tar.gz
    tar -xzf nvim.tar.gz
    cp -r nvim-linux64/* "$HOME/.nexus-shell/"
    rm -rf nvim.tar.gz nvim-linux64
fi
