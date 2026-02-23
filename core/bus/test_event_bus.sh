#!/bin/bash
# Test script for Nexus Event Bus

set -e

echo "=== Nexus Event Bus Test ==="
echo

# Setup
export NEXUS_PROJECT="test_project"
export USER=$(whoami)
SOCKET="/tmp/nexus_${USER}/${NEXUS_PROJECT}/bus.sock"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cleanup function
cleanup() {
    echo
    echo "Cleaning up..."
    if [[ -n "$BUS_PID" ]]; then
        kill "$BUS_PID" 2>/dev/null || true
    fi
    rm -rf "/tmp/nexus_${USER}/${NEXUS_PROJECT}"
    echo "Done."
}

trap cleanup EXIT

# Start event bus
echo "1. Starting event bus..."
mkdir -p "/tmp/nexus_${USER}/${NEXUS_PROJECT}"
python3 "$SCRIPT_DIR/event_server.py" > /tmp/bus_test.log 2>&1 &
BUS_PID=$!
echo "   PID: $BUS_PID"

# Wait for socket
echo "2. Waiting for socket..."
timeout=10
while [[ ! -S "$SOCKET" ]] && [[ $timeout -gt 0 ]]; do
    sleep 0.5
    ((timeout--))
done

if [[ ! -S "$SOCKET" ]]; then
    echo "   ERROR: Socket not created"
    cat /tmp/bus_test.log
    exit 1
fi
echo "   Socket created: $SOCKET"

# Test publish
echo "3. Testing publish..."
"$SCRIPT_DIR/nxs-event" publish TEST_EVENT '{"message":"Hello from test"}' && echo "   ✓ Publish successful" || echo "   ✗ Publish failed"

# Test subscribe (in background)
echo "4. Testing subscribe..."
"$SCRIPT_DIR/nxs-event" subscribe TEST_EVENT - > /tmp/test_events.log 2>&1 &
SUB_PID=$!
sleep 1

# Publish some events
echo "5. Publishing test events..."
for i in {1..3}; do
    "$SCRIPT_DIR/nxs-event" publish TEST_EVENT "{\"count\":$i,\"message\":\"Test event $i\"}"
    sleep 0.2
done

# Wait a bit for events to be received
sleep 1

# Kill subscriber
kill $SUB_PID 2>/dev/null || true

# Check results
echo "6. Checking received events..."
if [[ -f /tmp/test_events.log ]]; then
    event_count=$(grep -c '"type":"TEST_EVENT"' /tmp/test_events.log || echo "0")
    echo "   Received $event_count events"
    
    if [[ $event_count -ge 3 ]]; then
        echo "   ✓ Subscribe successful"
    else
        echo "   ✗ Subscribe failed (expected 3+ events)"
        echo "   Log contents:"
        cat /tmp/test_events.log
    fi
else
    echo "   ✗ No events received"
fi

# Test list
echo "7. Testing list..."
"$SCRIPT_DIR/nxs-event" list && echo "   ✓ List successful" || echo "   ✗ List failed"

# Test history
echo "8. Testing history..."
"$SCRIPT_DIR/nxs-event" history TEST_EVENT 5 && echo "   ✓ History successful" || echo "   ✗ History failed"

echo
echo "=== Test Complete ==="
echo "Event bus log:"
tail -20 /tmp/bus_test.log
