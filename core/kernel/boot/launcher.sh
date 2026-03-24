#!/bin/bash
# --- Nexus Station Launcher ---
# Thin shim: guards, path resolution, then delegates to Python.

set -e

# -- Sub-command routing (bypass boot for diagnostics) --
COMMAND_TYPE="$1"
[[ "$COMMAND_TYPE" == "boot" ]] && shift

# -- Guard: prevent circular/nested boot --
if [[ -n "$NEXUS_BOOT_IN_PROGRESS" ]] && [[ "$COMMAND_TYPE" != "audit" && "$COMMAND_TYPE" != "doctor" && "$COMMAND_TYPE" != "stop" ]]; then
    echo "[!] ERROR: Circular boot detected." >&2; exit 111
fi
export NEXUS_BOOT_IN_PROGRESS=1

if [[ -n "$NEXUS_STATION_ACTIVE" ]] && [[ "$COMMAND_TYPE" != "audit" && "$COMMAND_TYPE" != "doctor" && "$COMMAND_TYPE" != "stop" ]]; then
    echo "[!] ERROR: Station already active in this shell." >&2; exit 109
fi

if [[ -n "$TMUX" ]]; then
    CURRENT_SESSION=$(tmux display-message -p '#S' 2>/dev/null || echo "")
    if [[ "$CURRENT_SESSION" == nexus_* ]]; then
        echo "[!] ERROR: Already inside '$CURRENT_SESSION'." >&2; exit 110
    fi
fi

# -- Resolve NEXUS_HOME --
REAL_PATH="$0"
while [ -h "$REAL_PATH" ]; do
    DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"
    REAL_PATH="$(readlink "$REAL_PATH")"
    [[ $REAL_PATH != /* ]] && REAL_PATH="$DIR/$REAL_PATH"
done
SCRIPT_DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"
export NEXUS_HOME="$SCRIPT_DIR"
while [[ "$NEXUS_HOME" != "/" ]]; do
    [[ -d "$NEXUS_HOME/core" ]] && [[ -d "$NEXUS_HOME/config" ]] && break
    NEXUS_HOME="$(dirname "$NEXUS_HOME")"
done
export NEXUS_CORE="$NEXUS_HOME/core"
export NEXUS_KERNEL="$NEXUS_CORE/kernel"
export NEXUS_ENGINE="$NEXUS_CORE/engine"
export NEXUS_BOOT="$NEXUS_KERNEL/boot"
export NEXUS_SCRIPTS="$NEXUS_BOOT"
export PATH="$HOME/.nexus-shell/bin:$PATH"

# -- Resolve Python --
if [[ -x "$NEXUS_HOME/.venv/bin/python3" ]]; then
    PY="$NEXUS_HOME/.venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PY="python3"
else
    echo "[!] ERROR: Python 3 not found." >&2; exit 1
fi
export Python_BIN="$PY"

# -- Sub-command dispatch (before full boot) --
case "$COMMAND_TYPE" in
    stop)   source "$NEXUS_KERNEL/boot/stop.sh"; exit 0 ;;
    doctor) exec "$PY" "$NEXUS_KERNEL/bin/doctor" "${@:2}" ;;
    audit)  exec "$PY" "$NEXUS_ENGINE/diag/audit.py" ;;
    --help|-h)
        [[ -f "$NEXUS_KERNEL/boot/help.sh" ]] && { source "$NEXUS_KERNEL/boot/help.sh"; exit 0; } ;;
esac

# -- First-run check --
FIRST_RUN_FLAG="$HOME/.nexus/.first_run_complete"
if [[ ! -f "$FIRST_RUN_FLAG" ]] && [[ -z "$NEXUS_SKIP_FIRST_RUN" ]]; then
    echo "[*] First run detected. Launching setup wizard..."
    source "$NEXUS_KERNEL/boot/first_run.sh"
fi

# -- Boot: delegate to Python station module --
export PYTHONPATH="$NEXUS_CORE:${PYTHONPATH:-}"
BOOT_JSON=$("$PY" -m engine.station "$@")

# Parse the JSON result
CLIENT_SESSION=$(echo "$BOOT_JSON" | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('client_session',''))" 2>/dev/null || echo "")
SOCKET_LABEL=$(echo "$BOOT_JSON" | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('socket_label',''))" 2>/dev/null || echo "")
WINDOW_IDX=$(echo "$BOOT_JSON" | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('window_idx',0))" 2>/dev/null || echo "0")
STATUS=$(echo "$BOOT_JSON" | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "error")

if [[ "$STATUS" != "ok" ]]; then
    echo "[!] CRITICAL: Station boot failed." >&2; exit 1
fi

# -- Cleanup trap --
cleanup() {
    echo -e "\n\033[1;33m[*] Nexus Shutdown...\033[0m"
    pkill -P $$ 2>/dev/null || true
    [[ -f "$NEXUS_KERNEL/boot/boot_loader.sh" ]] && "$NEXUS_KERNEL/boot/boot_loader.sh" stop
    echo "[*] Cleanup complete."
}
trap cleanup EXIT SIGINT SIGTERM

# -- Momentum layout (apply saved pane sizes after attach resizes terminal) --
MOMENTUM_SCRIPT="/tmp/nexus_$(whoami)/momentum_layout.sh"
if [[ -f "$MOMENTUM_SCRIPT" ]]; then
    ( sleep 0.5; bash "$MOMENTUM_SCRIPT" 2>/dev/null ) &
fi

# -- Attach --
export NEXUS_STATION_ACTIVE=1
tmux -L "$SOCKET_LABEL" attach-session -t "$CLIENT_SESSION"
