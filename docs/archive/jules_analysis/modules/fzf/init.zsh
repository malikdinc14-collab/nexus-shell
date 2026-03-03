# modules/fzf/init.zsh

# Only source if not already configured
if [[ -z "$FZF_DEFAULT_OPTS" ]]; then
    export FZF_DEFAULT_OPTS="--height 40% --layout=reverse --border --inline-info"
    export FZF_DEFAULT_COMMAND="fd --type f --strip-cwd-prefix --hidden --follow --exclude .git"
    export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
fi

# Ensure bin is in path (redundant but safe)
[[ ":$PATH:" != *":$HOME/.nexus-shell/bin:"* ]] && export PATH="$HOME/.nexus-shell/bin:$PATH"
