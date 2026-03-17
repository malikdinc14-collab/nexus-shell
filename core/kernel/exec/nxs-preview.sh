#!/bin/bash
# core/kernel/exec/nxs-preview.sh
# Hotswaps from Editor to Renderer for the current file.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"

# 1. Query Neovim for current file
if [[ -S "$NVIM_PIPE" ]]; then
    FILE=$(nvim --server "$NVIM_PIPE" --remote-expr "expand('%:p')" 2>/dev/null)
else
    # Fallback to current pane's CWD or focused file if possible (future enhancement)
    exit 0
fi

if [[ -n "$FILE" && -f "$FILE" ]]; then
    # 2. Push to Local Stack (In-Place)
    "$NEXUS_HOME/core/kernel/stack/nxs-stack" push "local" "$NEXUS_HOME/core/ui/view/nxs-view '$FILE'" "Preview: $(basename "$FILE")"
fi
