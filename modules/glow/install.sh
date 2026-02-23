#!/bin/bash
BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

if [[ -x "$BIN_DIR/glow" ]]; then exit 0; fi

echo "    [glow] Downloading..."
GLOW_TAG=$(curl -sI https://github.com/charmbracelet/glow/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')
GLOW_VER="${GLOW_TAG#v}"
if [[ "$OS" == "macos" ]]; then
    URL="https://github.com/charmbracelet/glow/releases/download/${GLOW_TAG}/glow_${GLOW_VER}_Darwin_${ARCH}.tar.gz"
else
    URL="https://github.com/charmbracelet/glow/releases/download/${GLOW_TAG}/glow_${GLOW_VER}_Linux_${ARCH}.tar.gz"
fi

curl -sL "$URL" -o glow.tar.gz
mkdir -p glow_tmp
tar -xzf glow.tar.gz -C glow_tmp
find glow_tmp -type f -name "glow" -exec cp {} "$BIN_DIR/" \;
rm -rf glow.tar.gz glow_tmp
