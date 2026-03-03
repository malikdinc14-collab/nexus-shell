#!/bin/bash
# nexus-view - Rich media markdown renderer for Nexus-Shell
# Wraps glow and adds support for Mermaid and inline images

set -e

FILE="$1"
CACHE_DIR="/tmp/nexus/render"
mkdir -p "$CACHE_DIR"

IMGCAT="/Applications/iTerm.app/Contents/Resources/utilities/imgcat"

# If no file provided, read from stdin (for dynamic model output)
if [[ -z "$FILE" ]]; then
    TMP_IN="/tmp/nexus_view_in.md"
    cat > "$TMP_IN"
    FILE="$TMP_IN"
fi

# 1. Process Mermaid blocks
if grep -q "```mermaid" "$FILE"; then
    # Extract each mermaid block and render it
    BLOCK_COUNT=0
    # Simplified extraction logic: find lines between ```mermaid and ```
    sed -n '/```mermaid/,/```/p' "$FILE" | sed '/^```/d' > "$CACHE_DIR/current.mmd"
    
    # Render if mmdc is available
    if command -v mmdc > /dev/null 2>&1; then
        mmdc -i "$CACHE_DIR/current.mmd" -o "$CACHE_DIR/graph.png" -b transparent > /dev/null 2>&1
        # Display image via iTerm2 protocol
        if [[ -f "$CACHE_DIR/graph.png" ]]; then
            echo "📊 [Mermaid Diagram]"
            "$IMGCAT" "$CACHE_DIR/graph.png"
            echo ""
        fi
    else
        echo "⚠️  [Mermaid block detected but 'mmdc' not found. Run 'intel install-mermaid']"
    fi
fi

# 2. Render standard Markdown via glow
glow "$FILE"
