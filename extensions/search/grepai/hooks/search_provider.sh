#!/usr/bin/env bash
# extensions/grepai/hooks/search_provider.sh
# Provides semantic search capability to core/engine/search/

set -e

QUERY="${1:-}"
MODE="${2:-semantic}"
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

# Verify grepai is available
if ! command -v grepai &>/dev/null; then
    echo "[grepai] Not installed. Run: nxs extension install grepai" >&2
    exit 1
fi

# Ensure project is indexed
ensure_indexed() {
    if [[ ! -f "$PROJECT_ROOT/.grepai/index.db" ]]; then
        (cd "$PROJECT_ROOT" && grepai init >/dev/null 2>&1)
        (cd "$PROJECT_ROOT" && timeout 30 grepai index >/dev/null 2>&1 || true)
    fi
}

case "$MODE" in
    semantic|ai)
        # AI-powered semantic search
        ensure_indexed
        cd "$PROJECT_ROOT" && grepai search "$QUERY" 2>/dev/null
        ;;
    
    text|exact|grep)
        # Fall back to ripgrep for exact text matches
        if command -v rg &>/dev/null; then
            cd "$PROJECT_ROOT" && rg --column --line-number --no-heading --color=always "$QUERY" 2>/dev/null
        else
            cd "$PROJECT_ROOT" && grep -rn --color=always "$QUERY" 2>/dev/null
        fi
        ;;
    
    trace|callers)
        # Call graph: who calls this function?
        ensure_indexed
        cd "$PROJECT_ROOT" && grepai trace callers "$QUERY" 2>/dev/null
        ;;
    
    callees)
        # Call graph: what does this function call?
        ensure_indexed
        cd "$PROJECT_ROOT" && grepai trace callees "$QUERY" 2>/dev/null
        ;;
    
    functions|list)
        # List all indexed functions
        ensure_indexed
        cd "$PROJECT_ROOT" && grepai list functions 2>/dev/null
        ;;
    
    *)
        echo "Unknown search mode: $MODE" >&2
        echo "Modes: semantic, text, trace, callees, functions" >&2
        exit 1
        ;;
esac
