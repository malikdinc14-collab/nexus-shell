#!/bin/bash
# Record a terminal demo using asciinema
# Install: brew install asciinema

set -e

DEMO_NAME="${1:-parallax-demo}"
OUTPUT_DIR="$(dirname "$0")"

echo "Recording Parallax Demo"
echo "======================="
echo ""
echo "Tips for a good demo:"
echo "  1. Run 'parallax' to show the dashboard"
echo "  2. Navigate with arrow keys"
echo "  3. Show session linking (open another terminal)"
echo "  4. Execute an action"
echo "  5. Show settings/customization"
echo ""
echo "Press Ctrl+D or type 'exit' to stop recording"
echo ""

if ! command -v asciinema &>/dev/null; then
    echo "asciinema not found. Install with: brew install asciinema"
    exit 1
fi

# Record
asciinema rec "$OUTPUT_DIR/${DEMO_NAME}.cast" \
    --title "Parallax Demo" \
    --idle-time-limit 2

echo ""
echo "Recording saved to: $OUTPUT_DIR/${DEMO_NAME}.cast"
echo ""
echo "To convert to GIF (requires agg):"
echo "  agg ${DEMO_NAME}.cast ${DEMO_NAME}.gif"
echo ""
echo "To upload to asciinema.org:"
echo "  asciinema upload ${DEMO_NAME}.cast"
