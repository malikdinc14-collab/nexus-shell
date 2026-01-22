# zsh/core/adapters/editors/nvim.zsh

NVIM_PATH="nvim"
PIPE="/tmp/parallax-nvim.pipe"

edit_open() {
    # Resolve launch command
    echo "$NVIM_PATH --listen $PIPE"
}

edit_sync() {
    # $1: file, $2: line
    "$HOME/bin/px-context" set CURRENT_FILE "$1"
    "$HOME/bin/px-context" set CURRENT_LINE "$2"
}

edit_project() {
    # $1: content
    if [[ -S "$PIPE" ]]; then
        "$NVIM_PATH" --server "$PIPE" --remote-send "<esc>:enew<cr>i$1<esc>"
    else
        echo "Error: No active Neovim session at $PIPE" >&2
        return 1
    fi
}

edit_command() {
    # $1: cmd
    if [[ -S "$PIPE" ]]; then
        "$NVIM_PATH" --server "$PIPE" --remote-send ":$1<cr>"
    else
        echo "Error: No active Neovim session at $PIPE" >&2
        return 1
    fi
}
