#!/bin/bash
# IDENTITY: [SOVEREIGN.USER]
# PROJECT:  NEXUS CORE
# ACTION:   SEQUENTIAL IGNITION

# 1. Start Embedding Server (Jina)
if ! lsof -i:11435 > /dev/null; then
    echo "[*] Starting Jina Embedding Node..."
    nohup llama-server -m /Users/Shared/AI_CORE/models/embeddings/gguf/jina-code-embeddings-1.5b-GGUF/jina-code-embeddings-1.5b-Q8_0.gguf --port 11435 --embedding --host 127.0.0.1 > /Users/compute/nexus_embedding_server.log 2>&1 &
fi

# 2. Start Gateway
if ! lsof -i:11436 > /dev/null; then
    echo "[*] Starting Nexus Gateway..."
    nohup /Users/Shared/letta-backend/.venv/bin/python3 /Users/compute/workspace/scripts/nexus_gateway.py > /Users/compute/nexus_gateway.log 2>&1 &
fi

# 3. Start Model Node (Commander)
if ! lsof -i:1234 > /dev/null; then
    echo "[*] Starting Nexus Commander Node..."
    nohup /Users/compute/successor_venv/bin/python3 /Users/compute/workspace/scripts/nexus_launcher.py > /Users/compute/nexus_server.log 2>&1 &
fi

# 4. Start Letta Backend
if ! lsof -i:8283 > /dev/null; then
    echo "[*] Starting Letta Backend..."
    export LETTA_ENDPOINT="http://localhost:1234/v1"
    export LETTA_MODE="local"
    export OPENAI_API_BASE="http://localhost:1234/v1"
    export OPENAI_API_KEY="nexus-dummy-key"
    nohup /Users/Shared/letta-backend/letta-server > /Users/compute/nexus_custom_letta.log 2>&1 &
fi

# 5. Start Background Absorption
echo "[*] Triggering background project absorption..."
nohup bash /Users/compute/workspace/scripts/nexus_absorb_all.sh > /Users/compute/nexus_absorption.log 2>&1 &

echo "[✅] Nexus Ignition Sequence Complete."
