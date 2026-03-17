#!/usr/bin/env bash
# core/kernel/exec/dap_languages.sh
# Detects project language and launches the appropriate Debug Adapter.

FILE_PATH="${1:-}"
EXTENSION="${FILE_PATH##*.}"

case "$EXTENSION" in
    py)
        echo "[*] Detected Python. Launching debugpy..."
        # Check if debugpy is installed
        if ! python3 -m debugpy --version &>/dev/null; then
            echo "[!] Error: debugpy not found. Install with: pip install debugpy"
            exit 1
        fi
        # Launch headless debugpy server on port 5678
        python3 -m debugpy --listen 5678 "$FILE_PATH"
        ;;
    
    js|ts)
        echo "[*] Detected Node.js. Launching vscode-node-debug2..."
        # Launch node with inspector
        node --inspect-brk "$FILE_PATH"
        ;;

    *)
        echo "[!] Unsupported language for debugger: $EXTENSION"
        exit 1
        ;;
esac
