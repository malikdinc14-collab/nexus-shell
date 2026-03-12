#!/bin/bash
# modules/editor/lib/polymorphic_render.sh
# Detects file type and chooses the best TUI renderer.

FILE="${1}"
EXT="${FILE##*.}"

if [[ ! -f "$FILE" ]]; then
    echo "File not found: $FILE"
    exit 1
fi

# Selection Logic
case "$EXT" in
    md|markdown)
        if command -v glow &>/dev/null; then
            glow "$FILE"
        else
            bat --color=always --style=numbers "$FILE"
        fi
        ;;
    json|yaml|yml|toml|conf|sh|py|js|ts|java|c|cpp|rs)
        bat --color=always --style=numbers "$FILE"
        ;;
    pdf)
        # Using pdftotext or similar if available, otherwise fallback
        if command -v pdftotext &>/dev/null; then
            pdftotext "$FILE" - | bat --color=always --plain
        else
            echo "PDF rendering requires pdftotext. Showing raw content info:"
            file "$FILE"
        fi
        ;;
    *)
        # Default high-fidelity view
        bat --color=always --style=numbers "$FILE"
        ;;
esac
