#!/bin/bash
# core/kernel/exec/nxs-palette.sh
# Unified Command Palette (Omnibar) for Nexus Shell.
# Aggregates everything: Files, Commands, Compositions, Keybinds, Themes, and AI.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../../.." && pwd)}"
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && PY="$NEXUS_HOME/.venv/bin/python3" || PY=python3
DISPATCH="$NEXUS_HOME/core/engine/actions/dispatch.py"

SESSION_ID="${NEXUS_SESSION:-nexus_default}"
PROJECT_ROOT="${PROJECT_ROOT:-.}"

# ANSI Colors for FZF
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
GRAY='\033[0;90m'
NC='\033[0m'

# Helper to format items: "TYPE: Label | ACTION"
list_items() {
    # 1. Project Files (fd)
    if command -v fd &>/dev/null; then
        fd --type f --hidden --exclude .git . "$PROJECT_ROOT" | while read f; do
            echo "FILE: $(basename "$f") | $f"
        done
    fi

    # 2. Enabled Tools (from modules.conf)
    CONFIG_FILE="$NEXUS_HOME/config/modules.conf"
    if [[ -f "$CONFIG_FILE" ]]; then
        cat "$CONFIG_FILE" | tr ' ' '\n' | while read tool; do
            [[ -z "$tool" ]] && continue
            echo "TOOL: $tool | Launch $tool"
        done
    fi

    # 3. Core Commands (registry.json)
    python3 -c "
import json, os
nexus_home = os.getenv('NEXUS_HOME', '$NEXUS_HOME')
registry = json.load(open(os.path.join(nexus_home, 'core/engine/api/registry.json')))
for cmd in registry['commands']:
    name = cmd['names'][-1]
    desc = cmd.get('description', '')
    print(f'CMD: {name:<12} | {desc}')
"

    # 3. Compositions
    ls "$NEXUS_HOME/core/ui/compositions"/*.json 2>/dev/null | while read f; do
        name=$(basename "$f" .json)
        echo "COMP: $name | Launch layout"
    done

    # 4. Keybind Profiles
    ls "$NEXUS_HOME/config/keybinds"/*.conf 2>/dev/null | grep -v "active.conf" | while read f; do
        name=$(basename "$f" .conf)
        echo "KEY: $name | Switch keybind profile"
    done

    # 5. Themes
    ls "$NEXUS_HOME/core/ui/themes"/*.json 2>/dev/null | while read f; do
        name=$(basename "$f" .yaml)
        echo "THEME: $name | Apply color theme"
    done
}

# 2. The Fuzzy Picker with Multi-Action
# Keybinds mapping:
# enter       -> Open/Run
# shift-enter -> Render (for files)
# ctrl-e      -> Send to Agent (for files)
result=$(list_items | fzf --ansi --layout=reverse --border=rounded \
    --header="🚀 NEXUS OMNIBAR | [Enter] Open [Shift-Enter] Render [Ctrl-e] Brief AI" \
    --prompt="Execute > " \
    --expect="shift-enter,ctrl-e" \
    --color="header:cyan,prompt:yellow,pointer:green,hl:cyan" \
    --preview '
        TYPE=$(echo {} | cut -d: -f1);
        VAL=$(echo {} | cut -d"|" -f2 | xargs);
        if [[ "$TYPE" == "FILE" ]]; then
            bat --color=always --style=numbers --line-range=:100 "$VAL" 2>/dev/null || cat "$VAL";
        else
            echo "Action: $TYPE";
            echo "Target: $VAL";
        fi' \
    --preview-window=right:50%:wrap)

# Parse FZF result
key=$(echo "$result" | head -1)
selection=$(echo "$result" | tail -n +2)

if [[ -z "$selection" ]]; then exit 0; fi

TYPE=$(echo "$selection" | cut -d':' -f1 | xargs)
VALUE=$(echo "$selection" | cut -d'|' -f2 | xargs)
LABEL=$(echo "$selection" | cut -d'|' -f1 | cut -d':' -f2 | xargs)

# 3. Execution Dispatch
case "$TYPE" in
    FILE)
        if [[ "$key" == "shift-enter" ]]; then
            # RENDER — open in read-only/preview mode
            PYTHONPATH="$NEXUS_HOME/core" python3 -m engine.cli.nexus_ctl capability open editor -- --view "$VALUE"
        elif [[ "$key" == "ctrl-e" ]]; then
            # BRIEF AI (Send file context to agent)
            "$NEXUS_HOME/core/engine/ai/pi-gap.sh" "$VALUE"
        else
            # EDIT (Default) — open in editor via capability system
            PYTHONPATH="$NEXUS_HOME/core" python3 -m engine.cli.nexus_ctl capability open editor -- "$VALUE"
        fi
        ;;
    CMD)
        "$NEXUS_HOME/core/kernel/boot/dispatch.sh" "$LABEL"
        ;;
    COMP)
        "$PY" "$DISPATCH" pane.select-window "Nexus:$LABEL" 2>/dev/null
        ;;
    KEY)
        # Apply keybind profile via config handler
        PYTHONPATH="$NEXUS_HOME/core" python3 -m engine.cli.nexus_ctl config keymap "$LABEL"
        ;;
    THEME)
        "$NEXUS_HOME/core/kernel/boot/theme.sh" "$LABEL"
        ;;
    TOOL)
        # Launch tool via nxs-tab in the current pane
        "$NEXUS_HOME/core/kernel/exec/tabs.sh" "$LABEL" "new" "$LABEL"
        ;;
esac
