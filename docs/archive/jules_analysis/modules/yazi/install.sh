#!/bin/bash
BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

if [[ -x "$BIN_DIR/yazi" ]]; then exit 0; fi

echo "    [yazi] Downloading..."
YAZI_TAG=$(curl -sI https://github.com/sxyazi/yazi/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')

if [[ "$OS" == "macos" ]]; then
    URL="https://github.com/sxyazi/yazi/releases/download/${YAZI_TAG}/yazi-aarch64-apple-darwin.zip"
    curl -sL "$URL" -o yazi.zip
    unzip -q yazi.zip
    cp yazi-aarch64-apple-darwin/yazi "$BIN_DIR/"
    rm -rf yazi.zip yazi-aarch64-apple-darwin
else
    URL="https://github.com/sxyazi/yazi/releases/download/${YAZI_TAG}/yazi-x86_64-unknown-linux-gnu.zip"
    curl -sL "$URL" -o yazi.zip
    unzip -q yazi.zip
    cp yazi-x86_64-unknown-linux-gnu/yazi "$BIN_DIR/"
    rm -rf yazi.zip yazi-x86_64-unknown-linux-gnu
fi
