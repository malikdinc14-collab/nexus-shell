#!/bin/bash

# --- Nexus Theme Switcher ---
# Manages themes across tmux, nvim, and terminal

NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
THEMES_DIR="$NEXUS_HOME/themes"
ACTIVE_THEME_FILE="$NEXUS_STATE/theme.json"

ACTION="${1:-menu}"

list_themes() {
    for f in "$THEMES_DIR"/*.json; do
        basename "$f" .json
    done
}

get_active_theme() {
    if [[ -f "$ACTIVE_THEME_FILE" ]]; then
        # Extract theme name from JSON
        grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' "$ACTIVE_THEME_FILE" | head -1 | sed 's/.*"\([^"]*\)"$/\1/'
    else
        echo "nexus-cyber"
    fi
}

apply_theme() {
    local theme_name="$1"
    local theme_file="$THEMES_DIR/${theme_name}.json"
    
    if [[ ! -f "$theme_file" ]]; then
        echo "Theme not found: $theme_name"
        return 1
    fi
    
    # Copy theme to active state
    mkdir -p "$NEXUS_STATE"
    cp "$theme_file" "$ACTIVE_THEME_FILE"
    
    # Apply to tmux (read colors from theme)
    local bg=$(grep -o '"bg"[[:space:]]*:[[:space:]]*"[^"]*"' "$theme_file" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
    local fg=$(grep -o '"fg"[[:space:]]*:[[:space:]]*"[^"]*"' "$theme_file" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
    local border=$(grep -o '"border"[[:space:]]*:[[:space:]]*"[^"]*"' "$theme_file" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
    
    if [[ -n "$bg" && -n "$fg" ]]; then
        tmux set -g status-bg "$bg" 2>/dev/null
        tmux set -g status-fg "$fg" 2>/dev/null
        tmux set -g pane-border-style "fg=$border" 2>/dev/null
        tmux set -g pane-active-border-style "fg=$fg" 2>/dev/null
    fi
    
    tmux display-message "Theme: $theme_name"
    echo "Applied theme: $theme_name"
}

show_menu() {
    local current=$(get_active_theme)
    local themes=$(list_themes | while read t; do
        if [[ "$t" == "$current" ]]; then
            echo "$t|$t (current)"
        else
            echo "$t|$t"
        fi
    done)
    
    local selection=$(echo "$themes" | fzf --delimiter='|' --with-nth=2 \
        --header="Select Theme" \
        --reverse --height=50% --border \
        --color="fg:cyan,bg:black,hl:magenta,fg+:white,bg+:#1a1a2e,hl+:magenta")
    
    local theme="${selection%%|*}"
    
    if [[ -n "$theme" ]]; then
        apply_theme "$theme"
    fi
}

case "$ACTION" in
    "menu")
        show_menu
        ;;
    "list")
        list_themes
        ;;
    "current")
        get_active_theme
        ;;
    "apply")
        apply_theme "$2"
        ;;
    *)
        # Assume it's a theme name
        apply_theme "$ACTION"
        ;;
esac
