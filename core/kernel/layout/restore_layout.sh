#!/bin/bash
# restore_layout.sh (Momentum Edition)
# Reconstructs a "Frozen Moment" proportionally and structurally.

set -euo pipefail

WINDOW_ID="$1"
STATE_DATA="$2"
PROJECT_ROOT="${3:-.}"

# Axiom Invariant Check (P-03)
if [[ -z "$WINDOW_ID" ]]; then
    echo "FATAL: Invariant violated. WINDOW_ID is null." >&2
    exit 102
fi

# Resolve Python Binary
if [[ -x "${NEXUS_HOME:-}/.venv/bin/python3" ]]; then
    Python_BIN="$NEXUS_HOME/.venv/bin/python3"
elif command -v python3 &>/dev/null; then
    Python_BIN="python3"
else
    Python_BIN="python"
fi

# 1. Parse JSON and calculate current target dimensions
eval "$("$Python_BIN" -c "
import json, os, sys, subprocess

try:
    # Get current window dimensions
    res = subprocess.check_output(['tmux', 'display-message', '-t', '$WINDOW_ID', '-p', '#{window_width} #{window_height}']).decode().split()
    cur_w, cur_h = int(res[0]), int(res[1])

    # Load frozen moment
    # Axiom: Use environment variable to avoid shell escaping issues (P-02)
    s = json.loads(os.environ.get('STATE_JSON', '{}'))
    
    # Context Invariant (P-04): Use window-level root if available
    win_root = s.get('project_root', '$PROJECT_ROOT')
    print(f'WIN_ROOT=\"{win_root}\"')
    
    print(f'PANE_COUNT={len(s[\"panes\"])}')
    print(f'LAYOUT_STRING=\"{s[\"layout_string\"]}\"')
    
    for i, p in enumerate(s['panes']):
        # Map percentages to current pixels
        w_px = max(2, int(p['geom']['w_pct'] * cur_w))
        h_px = max(2, int(p['geom']['h_pct'] * cur_h))
        
        print(f'PANE_CMD_{i}=\"{p[\"command\"]}\"')
        print(f'PANE_TITLE_{i}=\"{p[\"title\"]}\"')
        print(f'PANE_W_{i}={w_px}')
        print(f'PANE_H_{i}={h_px}')
        print(f'PANE_CWD_{i}=\"{p.get(\"cwd\", win_root)}\"')
except Exception as e:
    sys.exit(1)
")"

echo "    [*] Reflowing session state ($PANE_COUNT panes) in $WIN_ROOT..."

# 2. Sequential Structural Restoration
# We start with the first pane (current window exists)
# Then we split off the rest based on percentages.
# Optimization: This version uses the layout_string as the primary structural hint
# but uses manual splits if the string fails due to major dimension mismatch.

# Prepare panes (Start with 1, add N-1)
for ((i=1; i<PANE_COUNT; i++)); do
    # Axiom: Each pane should ideally spawn in its own captured context
    eval "CWD=\$PANE_CWD_$i"
    tmux split-window -t "$WINDOW_ID" -c "$CWD" "/bin/zsh"
    sleep 0.05
done

# Apply Structural Layout
# We strip the checksum and try a forced layout apply
if ! tmux select-layout -t "$WINDOW_ID" "$LAYOUT_STRING" 2>/dev/null; then
    # Fallback to horizontal tiling if the structural string is rejected
    tmux select-layout -t "$WINDOW_ID" tiled
fi

# 3. Capture PIDs and Inject Tools
PANE_IDS=($(tmux list-panes -t "$WINDOW_ID" -F '#{pane_id}'))

for ((i=0; i<PANE_COUNT; i++)); do
    pane_id="${PANE_IDS[$i]}"
    cmd_var="PANE_CMD_$i"
    title_var="PANE_TITLE_$i"
    
    cmd="${!cmd_var}"
    title="${!title_var}"

    cmd="${cmd//\$Python_BIN/$Python_BIN}"
    cmd="${cmd//\$PARALLAX_CMD/$PARALLAX_CMD}"
    cmd="${cmd//\$EDITOR_CMD/$EDITOR_CMD}"
    cmd="${cmd//\$NEXUS_FILES/$NEXUS_FILES}"
    cmd="${cmd//\$NEXUS_CHAT/$NEXUS_CHAT}"
    cmd="${cmd//\$NEXUS_HOME/$NEXUS_HOME}"
    cmd="${cmd//\$PROJECT_ROOT/$PROJECT_ROOT}"

    # Freeze Script for Quoting Stability
    RESTORE_SCRIPT="/tmp/momentum_restore_${pane_id//%/_}.sh"
    echo "#!/bin/bash" > "$RESTORE_SCRIPT"
    echo "rm -f \"\$0\"" >> "$RESTORE_SCRIPT"
    echo "$cmd" >> "$RESTORE_SCRIPT"
    chmod +x "$RESTORE_SCRIPT"

    eval "CWD=\$PANE_CWD_$i"
    tmux select-pane -t "$pane_id" -T "$title"
    tmux respawn-pane -k -t "$pane_id" -c "$CWD" "$WRAPPER $RESTORE_SCRIPT"
done

# Final Pass: Ensure layout is applied one last time after PTY handshakes
tmux select-layout -t "$WINDOW_ID" "$LAYOUT_STRING" 2>/dev/null || true

# --- Slot Invariant Anchoring ---
idx=1
for p in $(tmux list-panes -t "$WINDOW_ID" -F '#{pane_id}'); do
    tmux set-option -p -t "$p" @nexus_slot "$idx"
    ((idx++))
done

echo "    [*] Momentum state restored."
