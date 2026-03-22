#!/usr/bin/env bash
# T092: Workspace save/restore roundtrip verification
set -euo pipefail

NEXUS_HOME="$(cd "$(dirname "$0")/../.." && pwd)"
CORE_DIR="$NEXUS_HOME/core"

PASS=0
FAIL=0

pass_check() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
fail_check() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

echo "============================================"
echo " T092: Workspace Save/Restore Roundtrip"
echo "============================================"
echo ""

# Create temp directory for session data
WORK_TMPDIR=$(mktemp -d)
trap 'rm -rf "$WORK_TMPDIR"' EXIT
echo "  Temp dir: $WORK_TMPDIR"
echo ""

# Run the roundtrip test via Python
echo "--- Running Roundtrip Test ---"
RESULT=$(SESSION_DIR="$WORK_TMPDIR" PYTHONPATH="$CORE_DIR" python3 -u <<'PYEOF'
import sys
import os
import json

from engine.stacks.stack import Tab, TabStack
from engine.stacks.manager import StackManager
from engine.momentum.stack_persistence import serialize_stacks, deserialize_stacks
from engine.momentum.session import save_session, restore_session

session_dir = os.environ["SESSION_DIR"]
errors = []

# --- Step 1: Create a StackManager with test data ---
mgr = StackManager()

tab_a = Tab(
    id="tab-a",
    capability_type="editor",
    adapter_name="neovim",
    command="nvim",
    cwd="/home/user/project",
    role="code",
    env={"EDITOR": "nvim"},
    is_active=False,
)
tab_b = Tab(
    id="tab-b",
    capability_type="terminal",
    adapter_name="zsh",
    command="zsh",
    cwd="/home/user",
    role="shell",
    env={},
    is_active=False,
)
tab_c = Tab(
    id="tab-c",
    capability_type="chat",
    adapter_name="opencode",
    command="opencode",
    cwd="/home/user/project",
    role="ai",
    env={"OPENCODE_MODEL": "gpt-4"},
    is_active=False,
)

mgr.push("%1", tab_a)
mgr.push("%1", tab_b)
mgr.push("%2", tab_c)

stacks_before = mgr.all_stacks()
pane_ids_before = sorted(stacks_before.keys())
tab_count_before = sum(len(s.tabs) for s in stacks_before.values())

print(f"CREATED: {len(pane_ids_before)} stacks, {tab_count_before} tabs")

# --- Step 2: Save session ---
save_session(mgr, session_dir)

stacks_file = os.path.join(session_dir, "stacks.json")
geometry_file = os.path.join(session_dir, "geometry.json")

if os.path.isfile(stacks_file):
    print("SAVE_STACKS: OK")
else:
    errors.append("stacks.json not created")
    print("SAVE_STACKS: FAIL")

if os.path.isfile(geometry_file):
    print("SAVE_GEOMETRY: OK")
else:
    errors.append("geometry.json not created")
    print("SAVE_GEOMETRY: FAIL")

# --- Step 3: Restore into a fresh manager ---
mgr2 = StackManager()
deferred = restore_session(mgr2, session_dir)

stacks_after = mgr2.all_stacks()
pane_ids_after = sorted(stacks_after.keys())
tab_count_after = sum(len(s.tabs) for s in stacks_after.values())

print(f"RESTORED: {len(pane_ids_after)} stacks, {tab_count_after} tabs")

# --- Step 4: Verify ---
if pane_ids_before == pane_ids_after:
    print("PANE_IDS: MATCH")
else:
    errors.append(f"Pane IDs differ: {pane_ids_before} vs {pane_ids_after}")
    print("PANE_IDS: MISMATCH")

if tab_count_before == tab_count_after:
    print("TAB_COUNT: MATCH")
else:
    errors.append(f"Tab count differs: {tab_count_before} vs {tab_count_after}")
    print("TAB_COUNT: MISMATCH")

# Check individual tab data integrity
for pane_id in pane_ids_before:
    original = stacks_before[pane_id]
    restored = stacks_after.get(pane_id)
    if restored is None:
        errors.append(f"Stack {pane_id} missing after restore")
        continue
    for i, (orig_tab, rest_tab) in enumerate(zip(original.tabs, restored.tabs)):
        if orig_tab.id != rest_tab.id:
            errors.append(f"Tab id mismatch in {pane_id}[{i}]: {orig_tab.id} vs {rest_tab.id}")
        if orig_tab.capability_type != rest_tab.capability_type:
            errors.append(f"Tab type mismatch in {pane_id}[{i}]")
        if orig_tab.adapter_name != rest_tab.adapter_name:
            errors.append(f"Tab adapter mismatch in {pane_id}[{i}]")
        if orig_tab.command != rest_tab.command:
            errors.append(f"Tab command mismatch in {pane_id}[{i}]")
        if orig_tab.cwd != rest_tab.cwd:
            errors.append(f"Tab cwd mismatch in {pane_id}[{i}]")
        if orig_tab.env != rest_tab.env:
            errors.append(f"Tab env mismatch in {pane_id}[{i}]")

if not errors:
    print("DATA_INTEGRITY: OK")
else:
    for e in errors:
        print(f"DATA_INTEGRITY: FAIL - {e}")

# Check deferred restore queued correctly
queued = deferred.pending_panes()
if len(queued) > 0:
    print(f"DEFERRED_QUEUE: OK ({len(queued)} panes queued)")
else:
    print("DEFERRED_QUEUE: EMPTY")

if errors:
    print("RESULT: FAIL")
    sys.exit(1)
else:
    print("RESULT: PASS")
    sys.exit(0)
PYEOF
) || true

echo "$RESULT"
echo ""

# Parse results
if echo "$RESULT" | grep -q "RESULT: PASS"; then
    pass_check "Workspace roundtrip save/restore"
else
    fail_check "Workspace roundtrip save/restore"
fi

if echo "$RESULT" | grep -q "PANE_IDS: MATCH"; then
    pass_check "Pane IDs preserved across save/restore"
else
    fail_check "Pane IDs not preserved"
fi

if echo "$RESULT" | grep -q "TAB_COUNT: MATCH"; then
    pass_check "Tab count preserved across save/restore"
else
    fail_check "Tab count not preserved"
fi

if echo "$RESULT" | grep -q "DATA_INTEGRITY: OK"; then
    pass_check "Tab data integrity verified"
else
    fail_check "Tab data integrity check failed"
fi

echo ""
echo "============================================"
TOTAL=$((PASS + FAIL))
echo " Results: $PASS passed, $FAIL failed (of $TOTAL checks)"
echo "============================================"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
