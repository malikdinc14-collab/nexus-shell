#!/bin/bash

# --- Nexus Render Daemon ---
# Watches state file and renders files using Glow/bat

NEXUS_CONFIG="${NEXUS_CONFIG:-$HOME/.config/nexus-shell}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"

# Load tools config
TOOLS_CONF="$NEXUS_CONFIG/tools.conf"
[[ -f "$TOOLS_CONF" ]] && source "$TOOLS_CONF"

# Tool defaults - use system PATH
GLOW="${NEXUS_RENDER:-glow}"

LAST_FILE="$NEXUS_STATE/last_path"
MODE_FILE="$NEXUS_STATE/editor_mode"
LAST_RENDERED=""

# Mark ourselves as in render mode
echo "render" > "$MODE_FILE"

cleanup() {
    echo "editor" > "$MODE_FILE"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Find glow - check PATH first, then common locations
find_glow() {
    if command -v "$GLOW" &>/dev/null; then
        echo "$GLOW"
    elif command -v glow &>/dev/null; then
        echo "glow"
    elif [[ -x "/opt/homebrew/bin/glow" ]]; then
        echo "/opt/homebrew/bin/glow"
    elif [[ -x "/usr/local/bin/glow" ]]; then
        echo "/usr/local/bin/glow"
    else
        echo ""
    fi
}

GLOW_CMD=$(find_glow)

clear
echo -e "\033[1;36m[ Nexus Render ]\033[0m"
echo "Waiting for file selection..."
echo ""
echo "Select a file in Yazi or use 'view <file>' from terminal"
if [[ -z "$GLOW_CMD" ]]; then
    echo -e "\033[1;33mNote: glow not found, using fallback rendering\033[0m"
fi

while true; do
    if [[ -f "$LAST_FILE" ]]; then
        CURRENT_FILE=$(cat "$LAST_FILE")
        
        if [[ "$CURRENT_FILE" != "$LAST_RENDERED" && -f "$CURRENT_FILE" ]]; then
            LAST_RENDERED="$CURRENT_FILE"
            EXT="${CURRENT_FILE##*.}"
            BASENAME=$(basename "$CURRENT_FILE")
            
            clear
            echo -e "\033[1;36m[ $BASENAME ]\033[0m"
            echo "──────────────────────────────────────────────────────"
            
            case "$EXT" in
                md|markdown|mdx)
                    # Markdown - render with Glow
                    if [[ -n "$GLOW_CMD" ]]; then
                        "$GLOW_CMD" -p "$CURRENT_FILE" 2>/dev/null || cat "$CURRENT_FILE"
                    else
                        cat "$CURRENT_FILE"
                    fi
                    ;;
                mmd|mermaid)
                    # Mermaid diagrams
                    echo -e "\033[1;33m[Mermaid Diagram]\033[0m"
                    cat "$CURRENT_FILE"
                    ;;
                json)
                    # JSON - pretty print
                    if command -v jq &>/dev/null; then
                        jq -C '.' "$CURRENT_FILE" 2>/dev/null || cat "$CURRENT_FILE"
                    else
                        cat "$CURRENT_FILE"
                    fi
                    ;;
                yaml|yml)
                    # YAML - syntax highlight if bat available
                    if command -v bat &>/dev/null; then
                        bat --style=plain --color=always --paging=never "$CURRENT_FILE" 2>/dev/null
                    else
                        cat "$CURRENT_FILE"
                    fi
                    ;;
                txt|text|"")
                    # Plain text - try Glow (handles markdown-like content)
                    if [[ -n "$GLOW_CMD" ]]; then
                        "$GLOW_CMD" -p "$CURRENT_FILE" 2>/dev/null || cat "$CURRENT_FILE"
                    else
                        cat "$CURRENT_FILE"
                    fi
                    ;;
                *)
                    # Other files - syntax highlight with bat if available
                    if command -v bat &>/dev/null; then
                        bat --style=plain --color=always --paging=never "$CURRENT_FILE" 2>/dev/null || cat "$CURRENT_FILE"
                    else
                        cat "$CURRENT_FILE"
                    fi
                    ;;
            esac
            
            echo ""
            echo "──────────────────────────────────────────────────────"
            echo -e "\033[0;90mCtrl+Space to return to Editor\033[0m"
        fi
    fi
    sleep 0.3
done
