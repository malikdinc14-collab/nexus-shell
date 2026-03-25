#!/bin/bash
# nexus-diagnostics.sh

echo "--- Nexus-Shell Diagnostics ---"
echo "Date: $(date)"
echo "OS: $(uname -a)"
echo "Tmux Version: $(tmux -V)"
echo "Zsh: $(which zsh || echo 'NOT FOUND')"
echo "Python3: $(python3 --version)"
echo "Fzf: $(which fzf || echo 'NOT FOUND')"
echo ""
echo "Testing tmux session creation..."
# Use a custom socket to avoid conflicts
SOCKET="/tmp/nexus_diag.sock"
rm -f "$SOCKET"
tmux -S "$SOCKET" new-session -d -s diag_session "echo 'test' && sleep 1" 2>&1
if [[ $? -eq 0 ]]; then
    echo "Tmux Session: OK"
    tmux -S "$SOCKET" kill-session -t diag_session 2>/dev/null
else
    echo "Tmux Session: FAILED"
fi
rm -f "$SOCKET"

echo ""
echo "Checking if pbcopy exists (macOS specific):"
which pbcopy || echo "pbcopy: NOT FOUND (Expected on Linux)"

echo "Checking if xclip exists (Linux clipboard fallback):"
which xclip || echo "xclip: NOT FOUND"
