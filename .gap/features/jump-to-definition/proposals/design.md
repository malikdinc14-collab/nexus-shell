# Design: Global Jump-to-Definition

## Flow
1.  User hits `Alt-j`.
2.  Tmux captures the current pane buffer.
3.  Regex extractor filters valid local files with line numbers.
4.  `fzf-tmux` popup allows the user to select the target.
5.  Shell script sends `nvim --server $PIPE --remote $FILE` followed by the line jump command.

## Tmux Binding
```tmux
bind-key -n M-j run-shell "core/kernel/nav/jump.sh"
```

## Nvim PRC Command
```bash
nvim --server "$PIPE" --remote "$FILE"
nvim --server "$PIPE" --remote-send ":$LINE<CR>zz"
```
