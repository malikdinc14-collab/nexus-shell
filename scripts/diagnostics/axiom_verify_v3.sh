#!/bin/bash
# scripts/axiom_verify_v3.sh
# Verifies T-3: save_layout.py --root flag

MOCK_ROOT="/tmp/nexus_mock_root"
mkdir -p "$MOCK_ROOT/.nexus"
rm -f "$MOCK_ROOT/.nexus/state.json"

echo "[Axiom] Verifying V-3: save_layout.py --root"

# Run save_layout with explicit root
# We use --window to keep it narrow
python3 core/kernel/layout/save_layout.py --root "$MOCK_ROOT" --window 0

if [[ -f "$MOCK_ROOT/.nexus/state.json" ]]; then
    echo "SUCCESS: state.json created in mock root."
    grep -q "session" "$MOCK_ROOT/.nexus/state.json"
    if [[ $? -eq 0 ]]; then
        echo "SUCCESS: session data found in state."
    else
        echo "FAILURE: session data missing."
        exit 1
    fi
else
    echo "FAILURE: state.json not found."
    exit 1
fi
