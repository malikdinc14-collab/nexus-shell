#!/bin/bash
# diagnose_momentum.sh — Full diagnostic for momentum save/restore
# Run AFTER a failed `nxs` boot (while the broken session is still up)
# OR run standalone to test the full save→restore cycle
#
# Usage:
#   bash tests/diagnose_momentum.sh          # standalone test
#   bash tests/diagnose_momentum.sh --live   # diagnose a live broken session

set -euo pipefail

NEXUS_HOME="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-standalone}"
USER=$(whoami)

RED='\033[1;31m'
GRN='\033[1;32m'
YLW='\033[1;33m'
CYN='\033[1;36m'
RST='\033[0m'

section() { echo -e "\n${CYN}═══ $1 ═══${RST}"; }
info()    { echo -e "${CYN}[INFO]${RST} $1"; }
warn()    { echo -e "${YLW}[WARN]${RST} $1"; }
err()     { echo -e "${RED}[ERR]${RST}  $1"; }
ok()      { echo -e "${GRN}[OK]${RST}   $1"; }

# ══════════════════════════════════════════
section "C1: DAEMON STATE"
# ══════════════════════════════════════════

DAEMON_PID_FILE="/tmp/nexus_${USER}/daemon.pid"
if [[ -f "$DAEMON_PID_FILE" ]]; then
    DAEMON_PID=$(cat "$DAEMON_PID_FILE")
    if kill -0 "$DAEMON_PID" 2>/dev/null; then
        ok "Daemon running (PID $DAEMON_PID)"

        # Check how old the daemon process is
        DAEMON_START=$(ps -p "$DAEMON_PID" -o lstart= 2>/dev/null || echo "unknown")
        info "Daemon started: $DAEMON_START"

        # Check if workspace.py is newer than daemon start
        WS_MOD=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$NEXUS_HOME/core/engine/orchestration/workspace.py" 2>/dev/null || echo "unknown")
        info "workspace.py last modified: $WS_MOD"
        warn "If workspace.py was modified AFTER daemon start, daemon is running STALE code!"
        warn "Fix: nxs stop && nxs (or kill $DAEMON_PID)"
    else
        err "Daemon PID file exists but process $DAEMON_PID is dead"
    fi
else
    warn "No daemon PID file found"
fi

# Check for multiple daemon instances
DAEMON_COUNT=$(pgrep -f "nexus.*daemon" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$DAEMON_COUNT" -gt 1 ]]; then
    err "Multiple daemon instances detected ($DAEMON_COUNT)! This explains 3x log lines."
    pgrep -fa "nexus.*daemon" 2>/dev/null || true
elif [[ "$DAEMON_COUNT" -eq 1 ]]; then
    ok "Single daemon instance"
else
    info "No daemon instances found (may have different process name)"
    # Try broader search
    DAEMON_COUNT2=$(pgrep -f "daemon.py" 2>/dev/null | wc -l | tr -d ' ')
    info "Processes matching 'daemon.py': $DAEMON_COUNT2"
    if [[ "$DAEMON_COUNT2" -gt 1 ]]; then
        err "Multiple daemon.py instances!"
        pgrep -fa "daemon.py" 2>/dev/null || true
    fi
fi

# ══════════════════════════════════════════
section "C3: DAEMON LOG (last boot)"
# ══════════════════════════════════════════

LOG_FILE="/tmp/nexus_${USER}/daemon.log"
if [[ -f "$LOG_FILE" ]]; then
    info "Log file: $LOG_FILE ($(wc -l < "$LOG_FILE") lines)"

    # Find the last boot_layout entry
    echo ""
    echo "--- Last momentum restore attempt ---"
    grep -n "Applying composition\|AXIOM-G\|scale\|Deferred\|hook\|Momentum\|BOOT\|ERROR\|WARNING\|Fatal" "$LOG_FILE" | tail -30
    echo ""

    # Check for the deferred hook log (my fix)
    if grep -q "Deferred layout apply via client-session-changed" "$LOG_FILE"; then
        ok "Deferred hook code is active (fix was picked up)"
    else
        if grep -q "Proportional layout applied (scale" "$LOG_FILE"; then
            err "OLD scaling code still running! Daemon has STALE code."
            warn ">>> RESTART THE DAEMON: kill the daemon process, then run nxs again <<<"
        else
            info "No layout restore found in log"
        fi
    fi

    # Check for Fatal Python errors
    FATAL_COUNT=$(grep -c "Fatal Python error" "$LOG_FILE" 2>/dev/null || echo 0)
    if [[ "$FATAL_COUNT" -gt 0 ]]; then
        warn "Found $FATAL_COUNT 'Fatal Python error' entries (stack init subprocess issue)"
    fi

    # Check for triple-logged lines
    TRIPLE=$(grep "\[orchestrator\]" "$LOG_FILE" | tail -20 | sort | uniq -c | sort -rn | head -5)
    MAX_DUPE=$(echo "$TRIPLE" | awk '{print $1}' | head -1)
    if [[ "$MAX_DUPE" -gt 1 ]]; then
        warn "Log lines duplicated ${MAX_DUPE}x — suggests multiple daemon instances or logging bug"
    fi
else
    warn "No daemon log found at $LOG_FILE"
fi

# ══════════════════════════════════════════
section "D1: STATE FILE"
# ══════════════════════════════════════════

STATE_FILE="$NEXUS_HOME/.nexus/state.json"
FALLBACK_DIR="$HOME/.nexus/storage"

if [[ -f "$STATE_FILE" ]]; then
    ok "Primary state file exists: $STATE_FILE"
    info "Size: $(wc -c < "$STATE_FILE") bytes"

    # Check if session.windows exists
    HAS_WINDOWS=$(.venv/bin/python3 -c "
import json
with open('$STATE_FILE') as f:
    data = json.load(f)
windows = data.get('session', {}).get('windows', {})
print(f'Windows: {list(windows.keys())}')
for idx, win in windows.items():
    panes = win.get('panes', [])
    dims = win.get('dimensions', {})
    layout = win.get('layout_string', 'NONE')
    print(f'  Window {idx}: {len(panes)} panes, dims={dims}, layout={layout[:60]}...')
    for p in panes:
        print(f'    [{p.get(\"index\")}] id={p.get(\"id\")}, cmd={p.get(\"command\", \"?\")[:50]}')
" 2>&1)
    echo "$HAS_WINDOWS"
else
    warn "No primary state file at $STATE_FILE"
    if [[ -d "$FALLBACK_DIR" ]]; then
        info "Fallback storage exists at $FALLBACK_DIR"
        find "$FALLBACK_DIR" -name "state.json" -exec echo "  Found: {}" \;
    fi
fi

# ══════════════════════════════════════════
section "B1/B2: TMUX ADAPTER vs RAW TMUX"
# ══════════════════════════════════════════

# Check what TmuxAdapter.apply_layout actually does
info "Checking TmuxAdapter.apply_layout implementation..."
ADAPTER_FILE="$NEXUS_HOME/core/engine/capabilities/adapters/tmux.py"
if [[ -f "$ADAPTER_FILE" ]]; then
    echo "--- apply_layout method ---"
    grep -A 15 "def apply_layout" "$ADAPTER_FILE" || echo "(not found)"
    echo ""
    echo "--- split method ---"
    grep -A 15 "def split" "$ADAPTER_FILE" | head -20 || echo "(not found)"
    echo ""
    echo "--- get_dimensions method ---"
    grep -A 10 "def get_dimensions" "$ADAPTER_FILE" | head -15 || echo "(not found)"
else
    err "TmuxAdapter not found at $ADAPTER_FILE"
fi

# ══════════════════════════════════════════
section "C4: LIVE SESSION STATE (if running)"
# ══════════════════════════════════════════

# Try to find any nexus tmux session
NEXUS_SOCKETS=$(ls /tmp/tmux-$(id -u)/ 2>/dev/null | grep nexus || echo "")
if [[ -z "$NEXUS_SOCKETS" ]]; then
    # Check for sockets in other locations
    NEXUS_SOCKETS=$(find /tmp -maxdepth 2 -name "nexus_*" -type s 2>/dev/null | head -5 || echo "")
fi

if [[ -n "$NEXUS_SOCKETS" ]]; then
    info "Found nexus sockets:"
    echo "$NEXUS_SOCKETS"

    # Try each socket
    for sock in $NEXUS_SOCKETS; do
        SOCK_NAME=$(basename "$sock")
        info "Checking socket: $SOCK_NAME"
        SESSIONS=$(tmux -L "$SOCK_NAME" list-sessions -F "#{session_name}" 2>/dev/null || echo "")
        if [[ -n "$SESSIONS" ]]; then
            for sess in $SESSIONS; do
                echo "  Session: $sess"
                PANES=$(tmux -L "$SOCK_NAME" list-panes -t "$sess" -F "#{pane_index}|#{@nexus_stack_id}|#{pane_width}x#{pane_height}|#{pane_left},#{pane_top}|#{pane_title}" 2>/dev/null || echo "none")
                echo "$PANES" | while IFS='|' read -r idx sid geo pos title; do
                    printf "    [%s] %-12s %s @ %-8s title=%s\n" "$idx" "$sid" "$geo" "$pos" "$title"
                done
                WIN_SIZE=$(tmux -L "$SOCK_NAME" display-message -t "$sess" -p "#{window_width}x#{window_height}" 2>/dev/null || echo "?")
                LAYOUT=$(tmux -L "$SOCK_NAME" list-windows -t "$sess" -F "#{window_layout}" 2>/dev/null || echo "?")
                echo "    Window size: $WIN_SIZE"
                echo "    Layout: $LAYOUT"
            done
        fi
    done
else
    info "No live nexus sessions found"
fi

# ══════════════════════════════════════════
section "A1: PANE ORDER CONSISTENCY"
# ══════════════════════════════════════════

info "Checking if saved pane order matches layout string leaf order..."
.venv/bin/python3 -c "
import json, re, sys

state_file = '$STATE_FILE'
try:
    with open(state_file) as f:
        data = json.load(f)
except:
    print('No state file to check')
    sys.exit(0)

windows = data.get('session', {}).get('windows', {})
for idx, win in windows.items():
    layout_str = win.get('layout_string', '')
    panes = win.get('panes', [])

    if not layout_str or not panes:
        print(f'Window {idx}: no layout string or panes')
        continue

    # Extract leaf pane IDs from layout string (in tree traversal order)
    # Pattern: WxH,X,Y,ID where ID is a leaf
    body = layout_str.split(',', 1)[1] if ',' in layout_str else layout_str

    # Find all leaf IDs: digits after the 4th number in a WxH,X,Y,ID group
    # that are NOT followed by { or [
    leaf_pattern = r'(\d+)x\d+,\d+,\d+,(\d+)'
    leaves = re.findall(leaf_pattern, body)
    leaf_ids = [int(lid) for _, lid in leaves]

    # Saved pane indices
    saved_indices = [p.get('index', -1) for p in panes]
    saved_ids = [p.get('id', '?') for p in panes]

    print(f'Window {idx}:')
    print(f'  Layout string leaf IDs (tree order): {leaf_ids}')
    print(f'  Saved pane indices:                  {saved_indices}')
    print(f'  Saved pane identities:               {saved_ids}')

    if len(leaf_ids) != len(saved_indices):
        print(f'  >>> MISMATCH: {len(leaf_ids)} leaves vs {len(saved_indices)} saved panes!')
    else:
        # Check if the ORDER of panes in state matches layout string leaf order
        # The remap function maps leaf[0] -> new_panes[0], leaf[1] -> new_panes[1], etc.
        # So saved_panes[0] must correspond to leaf[0], saved_panes[1] to leaf[1], etc.
        print(f'  Mapping: leaf ID {leaf_ids[0]} -> \"{saved_ids[0]}\", leaf ID {leaf_ids[1]} -> \"{saved_ids[1]}\", ...')
        print(f'  (If wrong identity appears in wrong pane, this mapping is the cause)')
" 2>&1

# ══════════════════════════════════════════
section "B4: PANE WRAPPER IMPACT"
# ══════════════════════════════════════════

WRAPPER="$NEXUS_HOME/core/kernel/boot/pane_wrapper.sh"
if [[ -f "$WRAPPER" ]]; then
    info "pane_wrapper.sh exists ($(wc -l < "$WRAPPER") lines)"
    echo "--- First 20 lines ---"
    head -20 "$WRAPPER"
else
    warn "pane_wrapper.sh not found at $WRAPPER"
fi

# ══════════════════════════════════════════
section "SUMMARY & RECOMMENDED NEXT STEPS"
# ══════════════════════════════════════════

echo ""
echo "Based on diagnostics above, check these in order:"
echo ""
echo "  1. Is the daemon running stale code? (Section C1)"
echo "     Fix: kill daemon, reboot nxs"
echo ""
echo "  2. Are there multiple daemon instances? (Section C1)"
echo "     Fix: pkill -f daemon.py, reboot nxs"
echo ""
echo "  3. Does apply_layout in TmuxAdapter work correctly? (Section B1/B2)"
echo "     Compare with raw tmux select-layout"
echo ""
echo "  4. Does the saved pane order match layout string order? (Section A1)"
echo "     If mismatched, identities will be in wrong panes"
echo ""
echo "  5. Does pane_wrapper.sh resize or modify the layout? (Section B4)"
echo "     Check if wrapper sends keys that trigger resize"
echo ""
