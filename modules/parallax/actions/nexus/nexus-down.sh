#!/bin/bash
# IDENTITY: [SOVEREIGN.USER]
# PROJECT:  NEXUS CORE
# ACTION:   GRACEFUL SHUTDOWN

echo "[*] Shutting down Nexus Core components..."

pkill -f letta.main
pkill -f uvicorn
pkill -f mlx_lm.server
pkill -f llama-server
pkill -f nexus_launcher.py
pkill -f nexus_gateway.py
pkill -f nexus_index.py
pkill -f nexus_fast_index.py

# Clean up database journals
rm -f ~/.letta/sqlite.db-wal ~/.letta/sqlite.db-shm

echo "[✅] Nexus Core Offline."
