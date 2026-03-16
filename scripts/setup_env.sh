#!/usr/bin/env bash
# scripts/setup_env.sh
# Establishes the Sovereign Environment (NSE) for Nexus Shell.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/nexus_env"

echo "[*] Establishing Sovereign Environment at $VENV_PATH..."

# 1. Create Virtual Environment
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
    echo "    [+] Virtual environment created."
else
    echo "    [i] Virtual environment already exists."
fi

# 2. Upgrade Pip
"$VENV_PATH/bin/pip" install --upgrade pip

# 3. Install Dependencies
echo "[*] Installing dependencies..."
"$VENV_PATH/bin/pip" install textual rapidfuzz pyyaml

echo "[✅] Sovereign Environment is READY."
echo "    Interpreter: $VENV_PATH/bin/python3"
