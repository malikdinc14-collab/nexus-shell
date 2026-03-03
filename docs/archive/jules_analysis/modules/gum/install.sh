#!/bin/bash
BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

if [[ -x "$BIN_DIR/gum" ]]; then exit 0; fi

echo "    [gum] Downloading..."
GUM_TAG=$(curl -sI https://github.com/charmbracelet/gum/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')
GUM_VER="${GUM_TAG#v}"
if [[ "$OS" == "macos" ]]; then
    URL="https://github.com/charmbracelet/gum/releases/download/${GUM_TAG}/gum_${GUM_VER}_Darwin_${ARCH}.tar.gz"
else
    URL="https://github.com/charmbracelet/gum/releases/download/${GUM_TAG}/gum_${GUM_VER}_Linux_${ARCH}.tar.gz"
fi

curl -sL "$URL" -o gum.tar.gz
mkdir -p gum_tmp
tar -xzf gum.tar.gz -C gum_tmp
find gum_tmp -type f -name "gum" -exec cp {} "$BIN_DIR/" \;
rm -rf gum.tar.gz gum_tmp
