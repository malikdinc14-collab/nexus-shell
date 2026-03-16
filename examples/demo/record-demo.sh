#!/bin/bash
# Record a terminal demo using asciinema
# Install: brew install asciinema

set -e

DEMO_NAME="${1:-nexus-shell-demo}"
OUTPUT_DIR="$(dirname "$0")"

echo "Recording Nexus-Shell Demo"
echo "=========================="
echo ""
echo "Tips for a good demo:"
echo "  1. cd to a sample project directory"
echo "  2. Run 'nexus' to start"
echo "  3. Show the 4-pane layout"
echo "  4. Demo 'edit file.txt' from terminal"
echo "  5. Demo 'view README.md' for render mode"
echo "  6. Show Ctrl+\\ commands (:help, :theme)"
echo "  7. Show navigation with Alt-Esc"
echo "  8. Exit with :q"
echo ""
echo "Press Ctrl+D or type 'exit' to stop recording"
echo ""

if ! command -v asciinema &>/dev/null; then
    echo "asciinema not found. Install with: brew install asciinema"
    exit 1
fi

# Record
asciinema rec "$OUTPUT_DIR/${DEMO_NAME}.cast" \
    --title "Nexus-Shell Demo" \
    --idle-time-limit 2

echo ""
echo "Recording saved to: $OUTPUT_DIR/${DEMO_NAME}.cast"
echo ""
echo "To convert to GIF (requires agg):"
echo "  agg ${DEMO_NAME}.cast ${DEMO_NAME}.gif"
echo ""
echo "To upload to asciinema.org:"
echo "  asciinema upload ${DEMO_NAME}.cast"
