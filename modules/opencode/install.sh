#!/bin/bash
BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

if [[ -x "$BIN_DIR/opencode" ]]; then exit 0; fi

echo "    [opencode] Downloading..."
OC_TAG=$(curl -sI https://github.com/anomalyco/opencode/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')

if [[ "$OS" == "macos" ]]; then
    URL="https://github.com/anomalyco/opencode/releases/download/${OC_TAG}/opencode-darwin-${ARCH}.zip"
    curl -sL "$URL" -o opencode.zip
    unzip -oq opencode.zip 2>/dev/null || true
else
    URL="https://github.com/anomalyco/opencode/releases/download/${OC_TAG}/opencode-linux-${ARCH}.tar.gz"
    curl -sL "$URL" -o opencode.tar.gz
    tar -xzf opencode.tar.gz 2>/dev/null || true
fi

if [[ -f "opencode" ]]; then
    cp opencode "$BIN_DIR/"
elif [[ -d "opencode_tmp" ]]; then
    find opencode_tmp -type f -name "opencode" -exec cp {} "$BIN_DIR/" \;
fi
rm -rf opencode opencode.zip opencode.tar.gz opencode_tmp
