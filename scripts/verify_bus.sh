#!/bin/bash
# scripts/verify_bus.sh
# Verifies that the active Nexus Event Bus is healthy.

USER=$(whoami)
PROJECT=$(basename "$(pwd)")
SOCKET="/tmp/nexus_$USER/$PROJECT/bus.sock"

echo "=== Nexus Event Bus Health Check ==="

# 1. Check Socket
if [[ -S "$SOCKET" ]]; then
    echo "✓ Event Bus socket found at $SOCKET"
else
    echo "✗ Event Bus socket not found for project $PROJECT"
    echo "  Hint: Is Nexus running? Try ./bin/nxs"
    exit 1
fi

# 2. Test Round-Trip
echo "2. Testing Event Round-Trip..."
RANDOM_VAL=$RANDOM
# Subscribe in background
nxs-event subscribe VERIFY_BUS | grep -m 1 "$RANDOM_VAL" > /tmp/bus_verify.tmp &
SUB_PID=$!

# Publish
sleep 0.5
nxs-event publish VERIFY_BUS "{\"status\":\"check\", \"nonce\":$RANDOM_VAL}"

# Wait for receipt
timeout 3 wait $SUB_PID
RESULT=$?

if [[ $RESULT -eq 0 ]]; then
    echo "✓ Round-trip successful (Received nonce $RANDOM_VAL)"
else
    echo "✗ Round-trip failed: Timeout waiting for event receipt."
    kill $SUB_PID 2>/dev/null
    exit 1
fi

# 3. Check Stats
echo "3. Checking Bus Statistics..."
nxs-event list | sed 's/^/   /'
echo "✓ Bus Health: EXCELLENT"
