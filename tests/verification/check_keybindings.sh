#!/usr/bin/env bash
# T091: Keybinding verification
set -euo pipefail

NEXUS_HOME="$(cd "$(dirname "$0")/../.." && pwd)"

PASS=0
FAIL=0
WARN=0

pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN + 1)); }

echo "============================================"
echo " T091: Nexus-Shell Keybinding Verification"
echo "============================================"
echo ""

# Expected Alt+key bindings: key -> description
declare -A EXPECTED_BINDINGS
EXPECTED_BINDINGS=(
    ["M-m"]="menu open"
    ["M-o"]="capability launcher"
    ["M-t"]="tab manager"
    ["M-n"]="new tab (stack push)"
    ["M-w"]="close tab (stack pop)"
    ["M-q"]="kill pane"
    ["M-["]="previous tab (rotate -1)"
    ["M-]"]="next tab (rotate 1)"
    ["M-v"]="vertical split"
    ["M-s"]="horizontal split"
    ["M-z"]="zoom toggle"
    ["M-g"]="lazygit popup"
)

# --- 1. Config file binding check ---
echo "--- Config File Bindings ---"
CONF_FILE="$NEXUS_HOME/config/tmux/nexus.conf"
if [[ ! -f "$CONF_FILE" ]]; then
    fail "nexus.conf not found"
    exit 1
fi

for key in "${!EXPECTED_BINDINGS[@]}"; do
    desc="${EXPECTED_BINDINGS[$key]}"
    if grep -q "bind-key -n $key" "$CONF_FILE" 2>/dev/null; then
        pass "Config has $key -> $desc"
    else
        fail "Config missing $key -> $desc"
    fi
done
echo ""

# --- 2. Conflict detection ---
echo "--- Binding Conflict Check ---"
# Extract all -n (root table) bind-key entries from the conf
KEYS_FOUND=$(grep -oP 'bind-key\s+-n\s+\K\S+' "$CONF_FILE" 2>/dev/null || true)
if [[ -z "$KEYS_FOUND" ]]; then
    warn "Could not parse any root-table bindings from config"
else
    CONFLICT_FOUND=false
    SORTED=$(echo "$KEYS_FOUND" | sort)
    DUPES=$(echo "$SORTED" | uniq -d)
    if [[ -n "$DUPES" ]]; then
        for dup in $DUPES; do
            fail "Binding conflict: $dup is mapped more than once"
            CONFLICT_FOUND=true
        done
    fi
    if [[ "$CONFLICT_FOUND" == "false" ]]; then
        pass "No binding conflicts detected ($(echo "$SORTED" | wc -l | tr -d ' ') unique root-table bindings)"
    fi
fi
echo ""

# --- 3. Live tmux verification ---
echo "--- Live tmux Binding Check ---"
if [[ -n "${TMUX:-}" ]]; then
    TMUX_KEYS=$(tmux list-keys 2>/dev/null || true)
    for key in "${!EXPECTED_BINDINGS[@]}"; do
        desc="${EXPECTED_BINDINGS[$key]}"
        if echo "$TMUX_KEYS" | grep -q "root.*$key"; then
            pass "tmux has $key -> $desc"
        else
            fail "tmux missing $key -> $desc"
        fi
    done
else
    warn "Not inside tmux — skipping live binding verification"
    echo "  The following bindings WOULD be checked in tmux:"
    for key in $(echo "${!EXPECTED_BINDINGS[@]}" | tr ' ' '\n' | sort); do
        echo "    $key -> ${EXPECTED_BINDINGS[$key]}"
    done
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
