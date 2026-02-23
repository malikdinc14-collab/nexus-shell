#!/bin/bash
BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

if [[ -x "$BIN_DIR/lazygit" ]]; then exit 0; fi

echo "    [lazygit] Downloading..."
LG_TAG=$(curl -sI https://github.com/jesseduffield/lazygit/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')
LG_VER="${LG_TAG#v}"

if [[ "$OS" == "macos" ]]; then
    URL="https://github.com/jesseduffield/lazygit/releases/download/${LG_TAG}/lazygit_${LG_VER}_darwin_${ARCH}.tar.gz"
else
    URL="https://github.com/jesseduffield/lazygit/releases/download/${LG_TAG}/lazygit_${LG_VER}_linux_${ARCH}.tar.gz" # Arch naming might vary for linux
fi

curl -sL "$URL" -o lazygit.tar.gz
mkdir -p lazygit_tmp
tar -xzf lazygit.tar.gz -C lazygit_tmp
find lazygit_tmp -type f -name "lazygit" -exec cp {} "$BIN_DIR/" \;
rm -rf lazygit.tar.gz lazygit_tmp
