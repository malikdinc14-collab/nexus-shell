# --- TMUX AUTOSTART ---
# Start tmux automatically for interactive shells
if [[ -o interactive && -z "$TMUX" && -z "$TMUX_AUTOSTARTED" ]]; then
  export TMUX_AUTOSTARTED=1
exec tmux new-session -A -s "main-$(tty | tr / _)"
fi

