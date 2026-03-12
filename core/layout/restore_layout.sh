#!/bin/bash
# restore_layout.sh — Restores a saved session state using tmux's native
# select-layout command for pixel-perfect geometry.
#
# Usage: restore_layout.sh <session_id:window> <state_file> <project_root>
#
# Strategy:
#   1. Read the saved state (layout_string + pane commands)
#   2. Create (N-1) additional blank panes (window starts with 1)
#   3. Apply the saved layout string via select-layout
#   4. Send each pane its command via respawn-pane

set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "$0")" && pwd)"
NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"
NEXUS_CORE="${NEXUS_CORE:-$NEXUS_HOME/core}"
WRAPPER="${WRAPPER:-$NEXUS_CORE/boot/pane_wrapper.sh}"

WINDOW_ID="$1"
STATE_DATA="$2"
PROJECT_ROOT="${3:-.}"
LOG_FILE="/tmp/nexus_restore_$(whoami).log"

echo "$(date) --- Restoring window $WINDOW_ID ---" >> "$LOG_FILE"

# Step 1: Parse JSON Context
# We use a heredoc to pass the JSON safely to Python to avoid shell quoting hell.
PARSE_CMD=$(cat <<EOF
import json, sys
try:
    s = json.loads('''$STATE_DATA''') if not '''$STATE_DATA'''.startswith('/') else json.load(open('''$STATE_DATA'''))
    print(f"LAYOUT_STRING='{s['layout_string']}'")
    print(f"PANE_COUNT={s['pane_count']}")
    for i, p in enumerate(s['panes']):
        print(f"PANE_TITLE_{i}='{p['title']}'")
        print(f"PANE_CMD_{i}='{p['command']}'")
except Exception as e:
    print(f"ERROR='{str(e)}'")
    sys.exit(1)
EOF
)

eval "$(python3 -c "$PARSE_CMD" 2>>"$LOG_FILE")" || {
    echo "    [!] ERROR: Failed to parse state data. See $LOG_FILE"
    exit 1
}

echo "    [*] Restoring saved session ($PANE_COUNT panes)..."

# 1. Create (N-1) extra panes (window already has 1)
for ((i=1; i<PANE_COUNT; i++)); do
    tmux split-window -t "$WINDOW_ID" -c "$PROJECT_ROOT" "/bin/zsh"
    sleep 0.05
done

# 2. Apply the saved layout string — this sets EXACT geometry
if ! tmux select-layout -t "$WINDOW_ID" "$LAYOUT_STRING" 2>>"$LOG_FILE"; then
    echo "    [!] WARNING: Could not apply exact pixel layout. Tmux will use defaults."
fi
sleep 0.2

# 3. Get the pane IDs in order (they match the saved order)
PANE_IDS=($(tmux list-panes -t "$WINDOW_ID" -F '#{pane_id}'))

# 4. For each pane, set its title and respawn with the saved command
for ((i=0; i<PANE_COUNT; i++)); do
    pane_id="${PANE_IDS[$i]}"
    
    # Get title and command from the variables we eval'd
    title_var="PANE_TITLE_$i"
    cmd_var="PANE_CMD_$i"
    title="${!title_var}"
    cmd="${!cmd_var}"
    
    # Expand Nexus environment variables in the command natively.
    # Do not use eval here, because pane_wrapper.sh will eval the final string.
    # Double-evaluating strips quotes and breaks paths with spaces.
    cmd="${cmd//\$PARALLAX_CMD/$PARALLAX_CMD}"
    cmd="${cmd//\$EDITOR_CMD/$EDITOR_CMD}"
    cmd="${cmd//\$NEXUS_FILES/$NEXUS_FILES}"
    cmd="${cmd//\$NEXUS_CHAT/$NEXUS_CHAT}"
    cmd="${cmd//\$NEXUS_HOME/$NEXUS_HOME}"
    cmd="${cmd//\$PROJECT_ROOT/$PROJECT_ROOT}"
    
    # --- ZERO ENTROPY EXECUTION ---
    # Tmux respawn-pane mangles quotes and complex bash variables.
    # To bypass all quoting hell, we write the exact command to an ephemeral 
    # script and tell tmux to execute that script through the wrapper.
    RESTORE_SCRIPT="/tmp/nexus_restore_pane_${pane_id//%/_}.sh"
    echo "#!/bin/bash" > "$RESTORE_SCRIPT"
    echo "rm -f \"\$0\"" >> "$RESTORE_SCRIPT" # Self-destruct after running
    echo "$cmd" >> "$RESTORE_SCRIPT"
    chmod +x "$RESTORE_SCRIPT"
    
    # Set title
    tmux select-pane -t "$pane_id" -T "$title"
    
    # Respawn pointing at the script
    tmux respawn-pane -k -t "$pane_id" -c "$PROJECT_ROOT" "$WRAPPER $RESTORE_SCRIPT"
    sleep 0.1
done

# 5. Re-apply layout one more time (respawn can shift things slightly)
tmux select-layout -t "$WINDOW_ID" "$LAYOUT_STRING"

# 6. Focus the editor pane if it exists
EDITOR_PANE=$(tmux list-panes -t "$WINDOW_ID" -F '#{pane_id} #{pane_title}' | grep -i editor | head -1 | awk '{print $1}')
if [[ -n "$EDITOR_PANE" ]]; then
    tmux select-pane -t "$EDITOR_PANE"
fi

echo "    [*] Session restored."
