#!/bin/bash
# modules/gptme/install.sh

BIN_DIR="${1:-$HOME/.nexus-shell/bin}"

# gptme is a Python tool, best installed via pipx or pip
if command -v gptme &>/dev/null; then
    echo "    [gptme] Already installed."
    exit 0
fi

echo "    [gptme] Installing via pip..."
if command -v pipx &>/dev/null; then
    pipx install gptme-python
elif command -v pip3 &>/dev/null; then
    pip3 install gptme-python --break-system-packages 2>/dev/null || pip3 install gptme-python
else
    echo "    [gptme] Error: python3/pip3 required."
    exit 1
fi

echo "    [gptme] Installed."
