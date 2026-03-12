#!/bin/bash
# core/exec/edit_helper.sh
# Reusable bridge for editing State Engine configurations via nvim.

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"
export NEXUS_CORE="${NEXUS_CORE:-$NEXUS_HOME/core}"
STATE_ENGINE="${NEXUS_CORE}/state/state_engine.sh"

PATH_TO_EDIT="$1" # e.g., ui.slots.chat.tool or ui.stacks.chat
LABEL="${2:-Configuration}"

if [[ -z "$PATH_TO_EDIT" ]]; then
    echo "Usage: $0 <state_path> [label]"
    exit 1
fi

TEMP_FILE="/tmp/nexus_edit_$(echo "$PATH_TO_EDIT" | tr '.' '_').tmp"

# 1. Fetch current value
CURRENT_VAL=$("$STATE_ENGINE" get "$PATH_TO_EDIT")

# 2. Write to temp file (handle JSON arrays vs single strings)
if [[ "$CURRENT_VAL" == "["* ]]; then
    echo "$CURRENT_VAL" | jq . > "$TEMP_FILE"
else
    echo "$CURRENT_VAL" > "$TEMP_FILE"
fi

# 3. Drop into Editor
# We use nvim if available, fallback to nano/vi
EDITOR_BIN="${NEXUS_EDITOR:-nvim}"
[[ -z "$(command -v "$EDITOR_BIN")" ]] && EDITOR_BIN="vi"

# Run editor
$EDITOR_BIN "$TEMP_FILE"

# 4. Read back and Sync
NEW_VAL=$(cat "$TEMP_FILE")

if [[ "$NEW_VAL" != "$CURRENT_VAL" ]]; then
    # Validate if it's supposed to be JSON
    if [[ "$CURRENT_VAL" == "["* ]]; then
        if ! echo "$NEW_VAL" | jq . >/dev/null 2>&1; then
            tmux display-message "Invalid JSON format. Check aborted."
            rm "$TEMP_FILE"
            exit 1
        fi
        # Minify for storage
        NEW_VAL=$(echo "$NEW_VAL" | jq -c .)
    fi

    "$STATE_ENGINE" set "$PATH_TO_EDIT" "$NEW_VAL"
    tmux display-message "Updated $LABEL: $NEW_VAL"
else
    tmux display-message "No changes made to $LABEL."
fi

rm "$TEMP_FILE"
