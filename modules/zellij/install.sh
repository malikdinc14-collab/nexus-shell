#!/bin/bash
# modules/zellij/install.sh

BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

if [[ -x "$BIN_DIR/zellij" ]]; then
    echo "    [zellij] Already installed."
    exit 0
fi

echo "    [zellij] Downloading zellij..."
VERSION="v0.40.1"

if [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
    Z_ARCH="aarch64"
else
    Z_ARCH="x86_64"
fi

if [[ "$OS" == "macos" ]]; then
    Z_OS="apple-darwin"
else
    Z_OS="unknown-linux-musl"
fi

URL="https://github.com/zellij-org/zellij/releases/download/${VERSION}/zellij-${Z_ARCH}-${Z_OS}.tar.gz"

curl -sL "$URL" -o zellij.tar.gz
tar -xzf zellij.tar.gz
cp zellij "$BIN_DIR/"
rm -f zellij.tar.gz zellij

echo "    [zellij] Installed to $BIN_DIR/zellij"
