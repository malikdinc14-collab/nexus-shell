# zsh/core/adapters/editors/generic.zsh

EDITOR_CMD="${PX_EDITOR:-${EDITOR:-nano}}"

edit_open() {
    echo "$EDITOR_CMD"
}

edit_sync() {
    # Generic editors don't support live sync yet
    "$HOME/bin/px-context" set CURRENT_FILE "$1"
}

edit_project() {
    # $1: content
    local tmp_file="/tmp/parallax_projection_$(date +%s).txt"
    echo "$1" > "$tmp_file"
    echo "PROJECTION: Saved to $tmp_file. Open manually in $EDITOR_CMD." >&2
}

edit_command() {
    echo "Error: Command action not supported for generic editors." >&2
    return 1
}
