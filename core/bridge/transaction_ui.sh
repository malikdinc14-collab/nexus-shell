#!/bin/bash
# transaction_ui.sh - Minimal TUI for approving/rejecting agent patches

# Robustness: Don't exit on errors
# set -e

# Resolve paths
NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
NEXUS_SCRIPTS="${NEXUS_SCRIPTS:-$NEXUS_HOME/core/boot}"

TRANS_DIR="$HOME/.parallax/transactions"
mkdir -p "$TRANS_DIR"

while true; do
    # Find latest staged transaction
    LATEST=$(ls -dt "$TRANS_DIR"/* 2>/dev/null | head -n 1 || true)
    
    clear
    echo "╔══════════════════════════════════════════╗"
    echo "║          TRANSACTION APPROVAL            ║"
    echo "╚══════════════════════════════════════════╝"
    
    if [[ -z "$LATEST" ]]; then
        echo ""
        echo "  (No pending transactions)"
        sleep 5
        continue
    fi

    ID=$(basename "$LATEST")
    METADATA="$LATEST/metadata.json"
    
    if [[ ! -f "$METADATA" ]]; then
        echo "  [Staging...] $ID"
        sleep 2
        continue
    fi

    # Use jq if available, fallback to grep
    if command -v jq &>/dev/null; then
        STATUS=$(jq -r '.status // "unknown"' "$METADATA" 2>/dev/null || echo "unknown")
        INTENT=$(jq -r '.intent // "N/A"' "$METADATA" 2>/dev/null || echo "N/A")
    else
        STATUS="unknown"
        INTENT="(jq not installed)"
    fi
    
    if [[ "$STATUS" != "staged" ]]; then
        echo "  Last: $ID ($STATUS)"
        sleep 5
        continue
    fi

    echo "  🆔 ID:     $ID"
    echo "  🎯 Intent: $INTENT"
    echo "--------------------------------------------"
    
    # Check verification
    VERIFY_LOG="$LATEST/verification.log"
    if [[ -f "$VERIFY_LOG" ]]; then
        if grep -q "FAIL" "$VERIFY_LOG" 2>/dev/null; then
            echo "  ⚠️  VERIFY: FAILED (See log)"
        elif grep -q "PASS" "$VERIFY_LOG" 2>/dev/null; then
            echo "  ✅ VERIFY: PASSED"
        else
            echo "  ⏳ VERIFY: Running..."
        fi
    fi

    echo ""
    echo "  [V]iew Diff  [A]pprove  [R]eject"
    
    # Wait for input
    read -n 1 -r KEY
    case "$KEY" in
        [vV])
            # Open diff in a popup or another pane
            PATCHES=$(ls "$LATEST"/*.patch)
            tmux display-popup -E -w 80% -h 80% "cat $PATCHES | glow -; echo 'Press Enter to return'; read"
            ;;
        [aA])
            echo -e "\nApplying..."
            "$NEXUS_SCRIPTS/px-patch.sh" apply "$ID"
            ;;
        [rR])
            echo -e "\nRejecting..."
            # Mark as rejected
            jq '.status = "rejected"' "$METADATA" > "$METADATA.tmp" && mv "$METADATA.tmp" "$METADATA"
            ;;
    esac
done
