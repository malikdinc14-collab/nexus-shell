#!/bin/bash
# test_momentum_layout.sh — Standalone momentum save/restore test
# Run this from a terminal (NOT inside tmux). It will:
#   1. Create a tmux session with the vscodelike layout (5 panes, hsplit+vsplit)
#   2. Capture the layout string and pane geometry
#   3. Kill the session
#   4. Recreate a session with 1 pane, then restore via momentum
#   5. Compare before/after geometry
#
# Usage: bash tests/test_momentum_layout.sh

set -e

SOCKET="test_momentum_$$"
SESSION="test_momentum"
NEXUS_HOME="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0

cleanup() {
    tmux -L "$SOCKET" kill-server 2>/dev/null || true
}
trap cleanup EXIT

log()  { echo -e "\033[1;36m[TEST]\033[0m $1"; }
pass() { echo -e "\033[1;32m[PASS]\033[0m $1"; PASS=$((PASS+1)); }
fail() { echo -e "\033[1;31m[FAIL]\033[0m $1"; FAIL=$((FAIL+1)); }

# ─── PHASE 1: Build a vscodelike layout manually ───
log "Phase 1: Building reference layout..."

# Create session with first pane
tmux -L "$SOCKET" new-session -d -s "$SESSION" -n "workspace_0" -x 160 -y 48

# Get the starting pane
P0=$(tmux -L "$SOCKET" list-panes -t "$SESSION" -F "#{pane_id}")

# hsplit: files (left 30%)
P_FILES=$(tmux -L "$SOCKET" split-window -t "$P0" -h -b -d -l 30% -P -F "#{pane_id}")

# The remaining pane after files split is now the rightmost
# hsplit: chat (right 45%)
P_CHAT=$(tmux -L "$SOCKET" split-window -t "$P0" -h -d -l 45% -P -F "#{pane_id}")

# Now P0 is the middle section. vsplit it for menu/editor/terminal
# vsplit: menu (top 20%)
P_MENU=$(tmux -L "$SOCKET" split-window -t "$P0" -v -b -d -l 20% -P -F "#{pane_id}")

# vsplit: terminal (bottom 25%)
P_TERM=$(tmux -L "$SOCKET" split-window -t "$P0" -v -d -l 25% -P -F "#{pane_id}")

# P0 is now the editor (middle of vsplit)
P_EDITOR="$P0"

# Label panes
tmux -L "$SOCKET" set-option -p -t "$P_FILES" @nexus_stack_id "files"
tmux -L "$SOCKET" set-option -p -t "$P_MENU" @nexus_stack_id "menu"
tmux -L "$SOCKET" set-option -p -t "$P_EDITOR" @nexus_stack_id "editor"
tmux -L "$SOCKET" set-option -p -t "$P_TERM" @nexus_stack_id "terminal"
tmux -L "$SOCKET" set-option -p -t "$P_CHAT" @nexus_stack_id "chat"

tmux -L "$SOCKET" select-pane -t "$P_FILES" -T "files"
tmux -L "$SOCKET" select-pane -t "$P_MENU" -T "menu"
tmux -L "$SOCKET" select-pane -t "$P_EDITOR" -T "editor"
tmux -L "$SOCKET" select-pane -t "$P_TERM" -T "terminal"
tmux -L "$SOCKET" select-pane -t "$P_CHAT" -T "chat"

sleep 0.3

# ─── PHASE 2: Capture reference state ───
log "Phase 2: Capturing reference layout..."

REF_LAYOUT=$(tmux -L "$SOCKET" list-windows -t "$SESSION" -F "#{window_layout}")
REF_PANE_COUNT=$(tmux -L "$SOCKET" list-panes -t "$SESSION" | wc -l | tr -d ' ')
REF_GEOMETRY=$(tmux -L "$SOCKET" list-panes -t "$SESSION" -F "#{pane_index}|#{@nexus_stack_id}|#{pane_width}x#{pane_height}|#{pane_left},#{pane_top}")
REF_WIN_SIZE=$(tmux -L "$SOCKET" display-message -t "$SESSION" -p "#{window_width}x#{window_height}")

echo ""
echo "=== REFERENCE STATE ==="
echo "Window size: $REF_WIN_SIZE"
echo "Pane count: $REF_PANE_COUNT"
echo "Layout string: $REF_LAYOUT"
echo "Pane geometry:"
echo "$REF_GEOMETRY" | while IFS='|' read -r idx sid geo pos; do
    printf "  [%s] %-10s %s @ %s\n" "$idx" "$sid" "$geo" "$pos"
done
echo ""

# Verify reference has 5 panes
if [[ "$REF_PANE_COUNT" -eq 5 ]]; then
    pass "Reference has 5 panes"
else
    fail "Reference has $REF_PANE_COUNT panes (expected 5)"
fi

# ─── PHASE 3: Kill session, recreate at 80x24 (simulating pre-attach) ───
log "Phase 3: Destroying and recreating session at 80x24 (pre-attach simulation)..."
tmux -L "$SOCKET" kill-session -t "$SESSION"
tmux -L "$SOCKET" new-session -d -s "$SESSION" -n "workspace_0" -x 80 -y 24
sleep 0.2

PREATTACH_SIZE=$(tmux -L "$SOCKET" display-message -t "$SESSION" -p "#{window_width}x#{window_height}")
log "Pre-attach window size: $PREATTACH_SIZE"

# ─── PHASE 4: Simulate momentum restore at 80x24 ───
log "Phase 4: Momentum restore — creating panes at 80x24..."

# Create 4 more panes (total 5) via horizontal splits
for i in 1 2 3 4; do
    tmux -L "$SOCKET" split-window -t "$SESSION" -h -d
    tmux -L "$SOCKET" select-layout -t "$SESSION" even-horizontal
done
sleep 0.2

NEW_PANE_COUNT=$(tmux -L "$SOCKET" list-panes -t "$SESSION" | wc -l | tr -d ' ')
if [[ "$NEW_PANE_COUNT" -eq 5 ]]; then
    pass "Momentum created 5 panes"
else
    fail "Momentum created $NEW_PANE_COUNT panes (expected 5)"
fi

# Get new pane IDs in order
NEW_PANES=$(tmux -L "$SOCKET" list-panes -t "$SESSION" -F "#{pane_id}")

# ─── PHASE 5A: Test BROKEN path — apply layout string at 80x24 ───
log "Phase 5A: Applying layout string at 80x24 (the BROKEN path)..."

REMAPPED=$(NEXUS_HOME="$NEXUS_HOME" .venv/bin/python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['NEXUS_HOME'], 'core/engine/orchestration'))
from workspace import WorkspaceOrchestrator

orch = WorkspaceOrchestrator.__new__(WorkspaceOrchestrator)
orch.ids_found = 0

new_panes = '''$NEW_PANES'''.strip().split('\n')
layout_str = '$REF_LAYOUT'

remapped = orch._remap_layout_string(layout_str, new_panes)
print(remapped)
" 2>&1)

echo "Remapped layout: $REMAPPED"

# Try applying at 80x24 — this is what the old code effectively did
APPLY_80=$(tmux -L "$SOCKET" select-layout -t "$SESSION" "$REMAPPED" 2>&1) || true

if [[ -z "$APPLY_80" ]]; then
    log "Layout accepted at 80x24 (surprising — let's see geometry)"
else
    log "Layout REJECTED at 80x24: $APPLY_80"
fi

GEOMETRY_80=$(tmux -L "$SOCKET" list-panes -t "$SESSION" -F "#{pane_index}|#{pane_width}x#{pane_height}|#{pane_left},#{pane_top}")
echo ""
echo "=== STATE AT 80x24 (after layout apply attempt) ==="
echo "$GEOMETRY_80" | while IFS='|' read -r idx geo pos; do
    printf "  [%s] %s @ %s\n" "$idx" "$geo" "$pos"
done

# ─── PHASE 5B: Now resize to 160x48 and see if layout survives ───
log "Phase 5B: Resizing window to 160x48 (simulating client attach)..."

# Create a client session and resize (simulating attach)
tmux -L "$SOCKET" new-session -d -t "$SESSION" -s "${SESSION}_client" -x 160 -y 48
sleep 0.3

POSTATTACH_SIZE=$(tmux -L "$SOCKET" display-message -t "${SESSION}_client" -p "#{window_width}x#{window_height}")
log "Post-attach window size: $POSTATTACH_SIZE"

GEOMETRY_AFTER_RESIZE=$(tmux -L "$SOCKET" list-panes -t "$SESSION" -F "#{pane_index}|#{pane_width}x#{pane_height}|#{pane_left},#{pane_top}")
echo ""
echo "=== STATE AFTER RESIZE TO 160x48 ==="
echo "$GEOMETRY_AFTER_RESIZE" | while IFS='|' read -r idx geo pos; do
    printf "  [%s] %s @ %s\n" "$idx" "$geo" "$pos"
done

# ─── PHASE 5C: Test FIXED path — apply AFTER resize ───
log "Phase 5C: Now applying layout string AFTER resize (the FIXED path)..."

# Kill client, recreate everything fresh
tmux -L "$SOCKET" kill-session -t "${SESSION}_client" 2>/dev/null || true
tmux -L "$SOCKET" kill-session -t "$SESSION"
tmux -L "$SOCKET" new-session -d -s "$SESSION" -n "workspace_0" -x 80 -y 24
sleep 0.2

for i in 1 2 3 4; do
    tmux -L "$SOCKET" split-window -t "$SESSION" -h -d
    tmux -L "$SOCKET" select-layout -t "$SESSION" even-horizontal
done
sleep 0.2

NEW_PANES2=$(tmux -L "$SOCKET" list-panes -t "$SESSION" -F "#{pane_id}")
REMAPPED2=$(NEXUS_HOME="$NEXUS_HOME" .venv/bin/python3 -c "
import sys, os
sys.path.insert(0, os.path.join(os.environ['NEXUS_HOME'], 'core/engine/orchestration'))
from workspace import WorkspaceOrchestrator

orch = WorkspaceOrchestrator.__new__(WorkspaceOrchestrator)
orch.ids_found = 0

new_panes = '''$NEW_PANES2'''.strip().split('\n')
layout_str = '$REF_LAYOUT'

remapped = orch._remap_layout_string(layout_str, new_panes)
print(remapped)
" 2>&1)

# DON'T apply yet — first resize via client attach
tmux -L "$SOCKET" new-session -d -t "$SESSION" -s "${SESSION}_client2" -x 160 -y 48
sleep 0.3

# NOW apply at real size
APPLY_FIXED=$(tmux -L "$SOCKET" select-layout -t "$SESSION" "$REMAPPED2" 2>&1) || true

if [[ -z "$APPLY_FIXED" ]]; then
    pass "Layout string applied successfully AFTER resize"
else
    fail "Layout string rejected after resize: $APPLY_FIXED"
fi

sleep 0.3

# ─── PHASE 6: Compare fixed path vs reference ───
log "Phase 6: Comparing FIXED restored vs reference..."

RESTORED_PANE_COUNT=$(tmux -L "$SOCKET" list-panes -t "$SESSION" | wc -l | tr -d ' ')
RESTORED_GEOMETRY=$(tmux -L "$SOCKET" list-panes -t "$SESSION" -F "#{pane_index}|#{pane_width}x#{pane_height}|#{pane_left},#{pane_top}")
RESTORED_WIN_SIZE=$(tmux -L "$SOCKET" display-message -t "${SESSION}_client2" -p "#{window_width}x#{window_height}")

echo ""
echo "=== RESTORED STATE ==="
echo "Window size: $RESTORED_WIN_SIZE"
echo "Pane count: $RESTORED_PANE_COUNT"
echo "Pane geometry:"
echo "$RESTORED_GEOMETRY" | while IFS='|' read -r idx geo pos; do
    printf "  [%s] %s @ %s\n" "$idx" "$geo" "$pos"
done
echo ""

# Compare pane count
if [[ "$RESTORED_PANE_COUNT" -eq "$REF_PANE_COUNT" ]]; then
    pass "Pane count matches ($RESTORED_PANE_COUNT)"
else
    fail "Pane count mismatch: restored=$RESTORED_PANE_COUNT, ref=$REF_PANE_COUNT"
fi

# Compare geometry (extract just WxH for each pane, sorted)
REF_SIZES=$(echo "$REF_GEOMETRY" | cut -d'|' -f3 | sort)
RESTORED_SIZES=$(echo "$RESTORED_GEOMETRY" | cut -d'|' -f2 | sort)

if [[ "$REF_SIZES" == "$RESTORED_SIZES" ]]; then
    pass "Pane sizes match exactly"
else
    echo "  Reference sizes:  $(echo $REF_SIZES | tr '\n' ' ')"
    echo "  Restored sizes:   $(echo $RESTORED_SIZES | tr '\n' ' ')"
    # Check if within 1 column/row tolerance (rounding)
    CLOSE=true
    paste <(echo "$REF_SIZES") <(echo "$RESTORED_SIZES") | while IFS=$'\t' read -r ref rest; do
        ref_w=$(echo "$ref" | cut -dx -f1)
        ref_h=$(echo "$ref" | cut -dx -f2)
        rest_w=$(echo "$rest" | cut -dx -f1)
        rest_h=$(echo "$rest" | cut -dx -f2)
        diff_w=$((ref_w - rest_w))
        diff_h=$((ref_h - rest_h))
        [[ ${diff_w#-} -le 1 && ${diff_h#-} -le 1 ]] || CLOSE=false
    done
    if $CLOSE 2>/dev/null; then
        pass "Pane sizes within ±1 tolerance"
    else
        fail "Pane sizes differ beyond tolerance"
    fi
fi

# Compare positions
REF_POS=$(echo "$REF_GEOMETRY" | cut -d'|' -f4 | sort)
RESTORED_POS=$(echo "$RESTORED_GEOMETRY" | cut -d'|' -f3 | sort)

if [[ "$REF_POS" == "$RESTORED_POS" ]]; then
    pass "Pane positions match exactly"
else
    echo "  Reference positions:  $(echo $REF_POS | tr '\n' ' ')"
    echo "  Restored positions:   $(echo $RESTORED_POS | tr '\n' ' ')"
    fail "Pane positions differ"
fi

# ─── SUMMARY ───
echo ""
echo "════════════════════════════════"
echo "  PASS: $PASS  |  FAIL: $FAIL"
echo "════════════════════════════════"

if [[ $FAIL -gt 0 ]]; then
    echo ""
    echo "Debug: Run these to inspect manually:"
    echo "  tmux -L $SOCKET attach -t $SESSION"
    echo "  tmux -L $SOCKET list-panes -t $SESSION -F '#{pane_index}|#{pane_width}x#{pane_height}|#{pane_left},#{pane_top}'"
    echo ""
    echo "(Session kept alive for inspection. Kill with: tmux -L $SOCKET kill-server)"
    trap - EXIT  # don't cleanup on failure
    exit 1
fi

exit 0
