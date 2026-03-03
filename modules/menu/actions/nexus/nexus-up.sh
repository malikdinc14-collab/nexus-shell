#!/bin/bash
# IDENTITY: [SOVEREIGN.USER]
# PROJECT:  NEXUS CORE
# ACTION:   SEQUENTIAL IGNITION

# 1. Start Embedding Server (Jina)
if ! lsof -i:11435 > /dev/null; then
    echo "[*] Starting Jina Embedding Node..."
    nohup llama-server -m /Users/Shared/AI_CORE/models/embeddings/gguf/jina-code-embeddings-1.5b-GGUF/jina-code-embeddings-1.5b-Q8_0.gguf --port 11435 --embedding --host 127.0.0.1 > /tmp/nexus_embedding_server.log 2>&1 &
fi

# 2. Start Gateway
if ! lsof -i:11436 > /dev/null; then
    echo "[*] Starting Nexus Gateway..."
    # Placeholder: requires a stable gateway path
    # nohup python3 "$NEXUS_HOME/core/api/nexus_gateway.py" > /tmp/nexus_gateway.log 2>&1 &
fi

# 3. Start Model Node (Commander)
if ! lsof -i:1234 > /dev/null; then
    echo "[*] Starting Nexus Commander Node..."
    # Placeholder: requires commander path
    # nohup python3 "$NEXUS_HOME/core/api/nexus_launcher.py" > /tmp/nexus_server.log 2>&1 &
fi

# 4. Start Letta Backend
if ! lsof -i:8283 > /dev/null; then
    echo "[*] Starting Letta Backend..."
    export LETTA_ENDPOINT="http://localhost:1234/v1"
    # nohup letta-server > /tmp/nexus_letta.log 2>&1 &
fi

# 5. Start Background Absorption
echo "[*] Triggering background project absorption..."
# nohup bash "$NEXUS_BOOT/nexus_absorb_all.sh" > /tmp/nexus_absorption.log 2>&1 &

echo "[✅] Nexus Ignition Sequence Complete."
