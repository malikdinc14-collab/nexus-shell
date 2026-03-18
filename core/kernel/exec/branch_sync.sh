#!/bin/bash
# core/kernel/exec/branch_sync.sh
# Orchestrates the shape-shifting of the Nexus workspace during a branch change.
# 1. Saves all current windows to the old branch.
# 2. Rebuilds all active windows using the new branch's state.

OLD_BRANCH="$1"
NEW_BRANCH="$2"

if [[ -z "$OLD_BRANCH" || -z "$NEW_BRANCH" || "$OLD_BRANCH" == "$NEW_BRANCH" ]]; then
    exit 0
fi

PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
SESSION_ID="nexus_$PROJECT_NAME"

# Abort if the session isn't running
if ! tmux has-session -t "$SESSION_ID" 2>/dev/null; then
    exit 0
fi

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
export NEXUS_HOME
export NEXUS_CORE="$NEXUS_HOME/core"
export PROJECT_ROOT

echo -e "\033[1;36m⚡ Nexus Shell: Branch Transition ($OLD_BRANCH → $NEW_BRANCH)\033[0m"

# 1. Save Current State to Old Branch
echo "  [*] Freezing current layout to $OLD_BRANCH..."
python3 "$NEXUS_KERNEL/layout/save_layout.py" --all --branch "$OLD_BRANCH" >/dev/null 2>&1

# 2. Get active window slots
WINDOWS=$(tmux list-windows -t "$SESSION_ID" -F '#{window_index}')

# 3. Create a temporary holding cell so tmux doesn't destroy the session when we wipe the windows
HOLDING_WIN="99"
tmux new-window -d -t "$SESSION_ID:$HOLDING_WIN" -n "nexus_transition" -c "$PROJECT_ROOT" "echo 'Branch Transition in Progress...'; sleep 10"

# 4. Wipe and Rebuild each Active Window
for WIN_IDX in $WINDOWS; do
    if [[ "$WIN_IDX" == "$HOLDING_WIN" ]]; then continue; fi
    
    echo "  [*] Submitting Window $WIN_IDX to $NEW_BRANCH shape-shift..."
    
    # Destroy the old window
    tmux kill-window -t "$SESSION_ID:$WIN_IDX" 2>/dev/null
    
    # Provision a fresh clean slot
    tmux new-window -d -t "$SESSION_ID:$WIN_IDX" -n "workspace_$WIN_IDX" -c "$PROJECT_ROOT" "/bin/zsh"
    
    # Command the Layout Engine to reconstruct the window using the new branch's saved state
    "$NEXUS_KERNEL/layout/layout_engine.sh" "$SESSION_ID:$WIN_IDX" "__saved_session__" "$SESSION_ID" "$PROJECT_ROOT" >/dev/null 2>&1
done

# 5. Destroy the holding cell
tmux kill-window -t "$SESSION_ID:$HOLDING_WIN" 2>/dev/null

echo -e "\033[1;32m  [*] Station Transition Complete.\033[0m"
