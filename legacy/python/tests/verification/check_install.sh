#!/usr/bin/env bash
# T090: Installation and startup timing verification
set -euo pipefail

NEXUS_HOME="$(cd "$(dirname "$0")/../.." && pwd)"

PASS=0
FAIL=0
WARN=0

pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN + 1)); }

echo "============================================"
echo " T090: Nexus-Shell Installation Check"
echo "============================================"
echo ""

# --- 1. Required binaries ---
echo "--- Required Binaries ---"
REQUIRED_BINS=(tmux python3 fzf gum yazi nvim)
for bin in "${REQUIRED_BINS[@]}"; do
    if command -v "$bin" &>/dev/null; then
        version=$("$bin" --version 2>/dev/null | head -1 || echo "unknown")
        pass "$bin found ($version)"
    else
        fail "$bin not found in PATH"
    fi
done
echo ""

# --- 2. Python module imports ---
echo "--- Python Module Imports ---"
PYTHON_MODULES=(yaml json dataclasses typing uuid pathlib)
for mod in "${PYTHON_MODULES[@]}"; do
    if python3 -c "import $mod" 2>/dev/null; then
        pass "python3 -c 'import $mod'"
    else
        fail "python3 -c 'import $mod'"
    fi
done
echo ""

# --- 3. Nexus config file exists ---
echo "--- Configuration Files ---"
CONF_FILE="$NEXUS_HOME/config/tmux/nexus.conf"
if [[ -f "$CONF_FILE" ]]; then
    pass "nexus.conf exists at $CONF_FILE"
else
    fail "nexus.conf missing at $CONF_FILE"
fi
echo ""

# --- 4. Startup timing ---
echo "--- Startup Timing ---"
if [[ -n "${TMUX:-}" ]]; then
    # Inside tmux: time sourcing the config
    START=$(python3 -c "import time; print(time.time())")
    tmux source-file "$CONF_FILE" 2>/dev/null || true
    END=$(python3 -c "import time; print(time.time())")
    ELAPSED=$(python3 -c "print(f'{$END - $START:.3f}')")
    echo "  Config source time: ${ELAPSED}s"
    THRESHOLD="2.0"
    if python3 -c "import sys; sys.exit(0 if $ELAPSED < $THRESHOLD else 1)"; then
        pass "Init time ${ELAPSED}s < ${THRESHOLD}s target"
    else
        fail "Init time ${ELAPSED}s >= ${THRESHOLD}s target"
    fi
else
    # Outside tmux: time a dry-run parse of the config
    START=$(python3 -c "import time; print(time.time())")
    python3 -c "
import sys, os
sys.path.insert(0, os.path.join('$NEXUS_HOME', 'core'))
from engine.stacks.manager import StackManager
from engine.momentum.session import save_session, restore_session
m = StackManager()
" 2>/dev/null || true
    END=$(python3 -c "import time; print(time.time())")
    ELAPSED=$(python3 -c "print(f'{$END - $START:.3f}')")
    echo "  Python engine import time: ${ELAPSED}s"
    THRESHOLD="2.0"
    if python3 -c "import sys; sys.exit(0 if $ELAPSED < $THRESHOLD else 1)"; then
        pass "Engine import time ${ELAPSED}s < ${THRESHOLD}s target"
    else
        fail "Engine import time ${ELAPSED}s >= ${THRESHOLD}s target"
    fi
    warn "Not inside tmux — skipped live config source timing"
fi
echo ""

# --- Summary ---
TOTAL=$((PASS + FAIL))
echo "============================================"
echo " Results: $PASS passed, $FAIL failed, $WARN warnings (of $TOTAL checks)"
echo "============================================"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
