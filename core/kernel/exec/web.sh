#!/bin/bash
# core/exec/nxs-web
# Nexus Web View Orchestrator
# Uses Carbonyl to render Web/MD/HTML/PDF content.

TARGET="${1}"
MODE="browser"

# 1. Dependency Check
if ! command -v carbonyl &> /dev/null; then
    echo "[!] Error: Carbonyl not found. Please install it or use 'nxs-web --install'."
    exit 1
fi

# 2. Logic: Detect Content Type
if [[ "$TARGET" == *.md ]]; then
    if ! command -v grip &> /dev/null; then
        echo "[*] Grip (Markdown renderer) not found. Attempting to install via pip..."
        pip install grip
    fi
    echo "[*] Starting Grip background service for $TARGET..."
    grip "$TARGET" --port 0 & # Port 0 finds an available port
    sleep 2
    # Find the port grip is running on (grip output usually says it)
    # For now, assume default 6419 or similar
    URL="http://localhost:6419"
elif [[ "$TARGET" == *.html ]]; then
    URL="file://$(realpath "$TARGET")"
elif [[ "$TARGET" == *.pdf ]]; then
    # Carbonyl (Chromium) handles PDFs via its internal viewer
    URL="file://$(realpath "$TARGET")"
elif [[ "$TARGET" == http* ]]; then
    URL="$TARGET"
else
    # Fallback/Default
    URL="${TARGET:-https://google.com}"
fi

# 3. Update State Engine
if [[ -n "$PROJECT_ROOT" && -f "$NEXUS_CORE/state/state_engine.sh" ]]; then
    "$NEXUS_CORE/state/state_engine.sh" set "ui.slots.web.url" "$URL"
fi

# 4. Launch Carbonyl
echo "[Nexus] Launching Web View: $URL"
carbonyl "$URL"
