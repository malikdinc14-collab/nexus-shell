#!/bin/bash
# core/boot/theme.sh — Nexus Theme Switcher
# Applies themes across tmux, nvim, and yazi from YAML theme files.

NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
THEMES_DIR="$NEXUS_HOME/config/themes"
SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null)
PROJECT_NAME=${SESSION_NAME#nexus_}
NVIM_PIPE="$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe"

PERSISTENT_STATE="$NEXUS_HOME/state"
mkdir -p "$PERSISTENT_STATE" 2>/dev/null
ACTIVE_THEME_FILE="$PERSISTENT_STATE/active_theme"

ACTION="${1:-menu}"

# Parse YAML value using python (lightweight, no deps beyond stdlib+pyyaml)
yaml_get() {
    local file="$1" key="$2"
    python3 -c "
import yaml
data = yaml.safe_load(open('$file'))
keys = '$key'.split('.')
v = data
for k in keys:
    v = v.get(k, '') if isinstance(v, dict) else ''
print(v or '')
" 2>/dev/null
}

list_themes() {
    for f in "$THEMES_DIR"/*.yaml; do
        basename "$f" .yaml
    done
}

get_active_theme() {
    if [[ -f "$ACTIVE_THEME_FILE" ]]; then
        cat "$ACTIVE_THEME_FILE"
    else
        echo "cyber"
    fi
}

apply_theme() {
    local theme_name="$1"
    local theme_file="$THEMES_DIR/${theme_name}.yaml"

    if [[ ! -f "$theme_file" ]]; then
        tmux display-message "Theme not found: $theme_name"
        return 1
    fi

    # Save active theme
    echo "$theme_name" > "$ACTIVE_THEME_FILE"

    # --- Apply to tmux ---
    local bg=$(yaml_get "$theme_file" "tmux.status_bg")
    local fg=$(yaml_get "$theme_file" "tmux.status_fg")
    local border=$(yaml_get "$theme_file" "tmux.border")
    local active_border=$(yaml_get "$theme_file" "tmux.active_border")
    local msg_bg=$(yaml_get "$theme_file" "tmux.message_bg")
    local msg_fg=$(yaml_get "$theme_file" "tmux.message_fg")
    local dim=$(yaml_get "$theme_file" "tmux.inactive_dim")

    [[ -n "$bg" ]] && tmux set -g status-bg "$bg"
    [[ -n "$fg" ]] && tmux set -g status-fg "$fg"
    [[ -n "$border" ]] && tmux set -g pane-border-style "fg=$border"
    [[ -n "$active_border" ]] && tmux set -g pane-active-border-style "fg=$active_border"
    [[ -n "$msg_bg" && -n "$msg_fg" ]] && tmux set -g message-style "bg=$msg_bg,fg=$msg_fg"
    [[ -n "$dim" ]] && tmux set -g window-style "$dim"
    tmux set -g window-active-style "fg=default,bg=default"

    # --- Apply to nvim ---
    if [[ -S "$NVIM_PIPE" ]]; then
        local colorscheme=$(yaml_get "$theme_file" "nvim.colorscheme")
        local background=$(yaml_get "$theme_file" "nvim.background")
        [[ -n "$background" ]] && nvim --server "$NVIM_PIPE" --remote-send ":set background=$background<CR>" 2>/dev/null
        [[ -n "$colorscheme" ]] && nvim --server "$NVIM_PIPE" --remote-send ":colorscheme $colorscheme<CR>" 2>/dev/null
    fi

    tmux display-message "Theme: $theme_name"
}

show_menu() {
    local current=$(get_active_theme)
    local selection=$(list_themes | while read t; do
        if [[ "$t" == "$current" ]]; then
            echo "● $t (active)"
        else
            echo "  $t"
        fi
    done | fzf --ansi --layout=reverse --border=rounded \
        --header="🎨 Select Theme" \
        --prompt="Theme > " | sed 's/^[● ]*//' | awk '{print $1}')

    if [[ -n "$selection" ]]; then
        apply_theme "$selection"
    fi
}

case "$ACTION" in
    menu)   show_menu ;;
    list)   list_themes ;;
    current) get_active_theme ;;
    apply)  apply_theme "$2" ;;
    *)      apply_theme "$ACTION" ;;
esac
