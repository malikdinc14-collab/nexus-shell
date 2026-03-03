#!/bin/bash
# modules/fzf/install.sh

BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

# Check system fzf first (Disabled for isolation compliance)
# if command -v fzf &>/dev/null; then
#    echo "    [fzf] System fzf found (Skipping download)."
#    exit 0
# fi

if [[ -x "$BIN_DIR/fzf" ]]; then
    echo "    [fzf] Nexus fzf already installed."
    exit 0
fi

echo "    [fzf] Downloading fzf..."
VERSION="0.67.0" 

# Map architecture
if [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
    F_ARCH="arm64"
else
    F_ARCH="amd64"
fi

if [[ "$OS" == "macos" || "$OS" == "Darwin" ]]; then
    URL="https://github.com/junegunn/fzf/releases/download/v${VERSION}/fzf-${VERSION}-darwin_${F_ARCH}.tar.gz"
else
    URL="https://github.com/junegunn/fzf/releases/download/v${VERSION}/fzf-${VERSION}-linux_${F_ARCH}.tar.gz"
fi

curl -sL "$URL" -o fzf.tar.gz
tar -xzf fzf.tar.gz
cp fzf "$BIN_DIR/"
rm -f fzf.tar.gz fzf

echo "    [fzf] Installed to $BIN_DIR/fzf"
