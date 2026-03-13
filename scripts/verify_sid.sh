#!/bin/bash
# scripts/verify_sid.sh
# Verifies that SID is running and broadcasting to the Event Bus.

USER=$(whoami)
PROJECT=$(basename "$(pwd)")
SOCKET="/tmp/nexus_$USER/$PROJECT/bus.sock"

echo "=== Nexus SID Verification ==="

# 1. Check if PID file/process exists
SID_PID=$(pgrep -f "python3.*core/ai/sid.py")
if [[ -n "$SID_PID" ]]; then
    echo "✓ SID process found (PID: $SID_PID)"
else
    echo "✗ SID process not found"
    exit 1
fi

# 2. Check if Bus Socket exists
if [[ -S "$SOCKET" ]]; then
    echo "✓ Event Bus socket found at $SOCKET"
else
    echo "✗ Event Bus socket not found"
    exit 1
fi

# 3. Listen for AI_STREAM events (Timeout after 5 seconds)
echo "3. Listening for SID signals (AI_STREAM)..."
timeout 5 nxs-event subscribe AI_STREAM | while read -r line; do
    echo "   [SIGNAL] $line"
    echo "✓ SID Broadcast detected"
    exit 0
done

if [[ $? -eq 124 ]]; then
    echo "✗ Timeout: No AI_STREAM signals detected from SID."
    echo "  (Make sure Agent Zero is active or try running 'nxs-ask hello')"
    exit 1
fi
