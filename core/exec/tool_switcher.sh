#!/bin/bash
# core/exec/tool_switcher.sh
# Interactive tool switcher for Nexus Shell.
# Displays a menu of tools for the current pane's role.

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"
export NEXUS_CORE="${NEXUS_CORE:-$NEXUS_HOME/core}"
STATE_ENGINE="${NEXUS_CORE}/state/state_engine.sh"

PANE_ID="$1"
ROLE=$(tmux show-option -p -t "$PANE_ID" @nexus_role | cut -d' ' -f2 | tr -d '"')

if [[ -z "$ROLE" || "$ROLE" == "null" ]]; then
    # Fallback to menu if no role
    "$NEXUS_CORE/boot/pane_wrapper.sh" "$NEXUS_HOME/modules/menu/bin/nexus-menu"
    exit 0
fi

# Get Stack from State Engine
STACK=$("$STATE_ENGINE" get "ui.stacks.$ROLE")

# If stack is empty or not an array, offer default tools
if [[ -z "$STACK" || "$STACK" == "{}" || "$STACK" == "null" ]]; then
    case "$ROLE" in
        chat) OPTIONS=("pi" "opencode" "aider" "gptme") ;;
        editor) OPTIONS=("nvim" "micro") ;;
        files) OPTIONS=("yazi" "ranger") ;;
        *) OPTIONS=("/bin/zsh") ;;
    esac
else
    # Parse JSON array to newline-separated list
    OPTIONS=($(echo "$STACK" | jq -r '.[]'))
fi

# Add "Nexus Menu" and "Shell" to every list
OPTIONS+=("---" "Nexus Menu" "Bash Shell")

# Show FZF Menu with Edit Support (Alt-E)
CHOICE=$(printf "%s\n" "${OPTIONS[@]}" | fzf \
    --header="Switch Tool [$ROLE] (Alt-E: Edit Stack)" \
    --reverse --height=10 \
    --bind "alt-e:execute(${NEXUS_CORE}/exec/edit_helper.sh ui.stacks.$ROLE 'Stack [$ROLE]')+reload(printf '%s\n' \$($STATE_ENGINE get ui.stacks.$ROLE | jq -r '.[]' 2>/dev/null || echo '') '---' 'Nexus Menu' 'Bash Shell')")

[[ -z "$CHOICE" || "$CHOICE" == "---" ]] && exit 0

case "$CHOICE" in
    "Nexus Menu")
        CMD="$NEXUS_HOME/modules/menu/bin/nexus-menu"
        ;;
    "Bash Shell")
        CMD="/bin/zsh -i"
        ;;
    *)
        CMD="$CHOICE"
        # Update State Engine so it persists
        "$STATE_ENGINE" set "ui.slots.$ROLE.tool" "$CHOICE"
        ;;
esac

# Swap the tool
tmux respawn-pane -k -t "$PANE_ID" "$NEXUS_CORE/boot/pane_wrapper.sh $CMD"
