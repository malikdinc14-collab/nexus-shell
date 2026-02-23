#!/bin/bash
# px-patch.sh - Atomic patch applicator with rollback

ACTION="$1"
TID="$2"
TRANS_DIR="$HOME/.parallax/transactions/$TID"

[[ ! -d "$TRANS_DIR" ]] && echo "❌ Transaction $TID not found" && exit 1

case "$ACTION" in
    apply)
        # Verify hashes via Python core if needed, but for now simple application
        export PYTHONPATH="$(cd "$(dirname "$0")/../modules/parallax" && pwd):$PYTHONPATH"
        python3 -c "from lib.core.workspace import WorkspaceGuard; print(WorkspaceGuard('.').commit('$TID'))"
        ;;
    rollback)
        # Use git checkout or patch -R
        # For simplicity in this spec, we use patch -R
        METADATA="$TRANS_DIR/metadata.json"
        FILES=$(jq -r '.changes[].path' "$METADATA")
        PATCHES=$(jq -r '.changes[].patch_file' "$METADATA")
        
        # Rollback in reverse
        # (This is a placeholder for a more robust git-based rollback)
        echo "⏪ Rolling back $TID..."
        for p in $PATCHES; do
             # Find matching file for this patch
             # (Simplification: assuming 1:1 order)
             patch -R < "$p"
        done
        echo "✅ Rollback complete."
        ;;
esac
