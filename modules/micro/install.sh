#!/bin/bash
BIN_DIR="${1:-$HOME/.nexus-shell/bin}"
OS="${2:-macos}"
ARCH="${3:-arm64}"

if [[ -x "$BIN_DIR/micro" ]]; then exit 0; fi
echo "    [micro] Downloading..."
curl https://getmic.ro | bash
mv micro "$BIN_DIR/" 2>/dev/null
