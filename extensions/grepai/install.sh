#!/usr/bin/env bash
# extensions/grepai/install.sh

set -e

echo "[grepai] Installing semantic search extension..."

# Detect OS and install
case "$OSTYPE" in
    darwin*)
        if command -v brew &>/dev/null; then
            echo "[grepai] Installing via Homebrew..."
            brew install yoanbernabeu/tap/grepai
        else
            echo "[grepai] Installing via curl..."
            curl -sSL https://raw.githubusercontent.com/yoanbernabeu/grepai/main/install.sh | sh
        fi
        ;;
    linux*)
        echo "[grepai] Installing via curl..."
        curl -sSL https://raw.githubusercontent.com/yoanbernabeu/grepai/main/install.sh | sh
        ;;
    *)
        echo "[grepai] Unsupported OS: $OSTYPE"
        echo "       Visit: https://github.com/yoanbernabeu/grepai"
        exit 1
        ;;
esac

# Verify installation
if ! command -v grepai &>/dev/null; then
    echo "[grepai] ✗ Installation failed"
    exit 1
fi

VERSION=$(grepai version 2>/dev/null || echo "unknown")
echo "[grepai] ✓ Installed: grepai $VERSION"

# Check embedding provider
echo ""
if ! command -v ollama &>/dev/null; then
    echo "[grepai] ⚠ Ollama not found (required for local embeddings)"
    echo ""
    echo "    To enable local embeddings:"
    echo "    1. curl -fsSL https://ollama.ai/install.sh | sh"
    echo "    2. ollama pull nomic-embed-text"
    echo ""
else
    if ! ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
        echo "[grepai] ⚠ nomic-embed-text model not found"
        echo "    Run: ollama pull nomic-embed-text"
    else
        echo "[grepai] ✓ Ollama + nomic-embed-text ready"
    fi
fi

echo ""
echo "[grepai] Usage:"
echo "    nxs-grepai search \"error handling\""
echo "    nxs-grepai trace callers \"Login\""
echo ""
