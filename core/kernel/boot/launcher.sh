#!/bin/bash
# --- Nexus Supervisor: SIMPLIFIED ROBUST EDITION ---
# Enforces stability through "Session-First" logic.

set -e

# 1. Sub-Command Routing (Direct access for diagnostics/management)
COMMAND_TYPE="$1"
case "$COMMAND_TYPE" in
    boot)
        shift ;;
esac

# 0. Early State Cleanup (Before any session checks)
# This ensures a clean slate for critical components like the nvim pipe.
# Note: NEXUS_STATE is not yet defined, so we use the explicit path.
rm -rf "/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe" 2>/dev/null

# 1.1 Process Genealogy Guard (Detect nested nxs calls)
# Allow diagnostic/management commands to bypass this check
if [[ -n "$NEXUS_BOOT_IN_PROGRESS" ]] && [[ "$COMMAND_TYPE" != "audit" && "$COMMAND_TYPE" != "doctor" && "$COMMAND_TYPE" != "stop" ]]; then
    echo "[!] ERROR: Circular boot detected. Aborting." >&2
    exit 111
fi
export NEXUS_BOOT_IN_PROGRESS=1

# 2. Physical Path Resolution (Smart Discovery)
REAL_PATH="$0"
while [ -h "$REAL_PATH" ]; do
    DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"
    REAL_PATH="$(readlink "$REAL_PATH")"
    [[ $REAL_PATH != /* ]] && REAL_PATH="$DIR/$REAL_PATH"
done
SCRIPT_DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"

# Walk up until we find core/
export NEXUS_HOME="$SCRIPT_DIR"
while [[ "$NEXUS_HOME" != "/" ]]; do
    if [[ -d "$NEXUS_HOME/core" ]] && [[ -d "$NEXUS_HOME/config" ]]; then
        break
    fi
    NEXUS_HOME="$(dirname "$NEXUS_HOME")"
done
export NEXUS_CORE="$NEXUS_HOME/core"
export NEXUS_KERNEL="$NEXUS_CORE/kernel"
export NEXUS_ENGINE="$NEXUS_CORE/engine"
export NEXUS_UI="$NEXUS_CORE/ui"
export NEXUS_SERVICES="$NEXUS_CORE/services"
export NEXUS_BOOT="$NEXUS_KERNEL/boot"
export NEXUS_SCRIPTS="$NEXUS_BOOT"

# 2. Resolve Python Binary (Move early so helpers can use it)
if [[ -x "$NEXUS_HOME/.venv/bin/python3" ]]; then
    Python_BIN="$NEXUS_HOME/.venv/bin/python3"
elif command -v python3 &>/dev/null; then
    Python_BIN="python3"
else
    echo "[!] ERROR: Python 3 not found." >&2
    exit 1
fi
export Python_BIN

# Start the Sovereign Daemon & Core Services (Python-Orchestrated)
"$Python_BIN" "$NEXUS_ENGINE/lib/daemon_client.py" ensure || { echo "[!] CRITICAL: Daemon failure." >&2; exit 1; }

# 2. Environment & Identity
PROFILE_DIR="$HOME/.nexus"
PROFILE_FILE="$PROFILE_DIR/profile.yaml"
FIRST_RUN_FLAG="$PROFILE_DIR/.first_run_complete"

# 2.2 Sub-Command Execution
case "$COMMAND_TYPE" in
    stop)
        source "$NEXUS_KERNEL/boot/stop.sh"
        exit 0 ;;
    doctor)
        exec "$Python_BIN" "$NEXUS_KERNEL/bin/doctor" "${@:2}" ;;
    audit)
        exec "$Python_BIN" "$NEXUS_ENGINE/diag/audit.py" ;;
    --help|-h)
        if [[ -f "$NEXUS_KERNEL/boot/help.sh" ]]; then
            source "$NEXUS_KERNEL/boot/help.sh"
            exit 0
        fi ;;
esac


# 3. Identity Guard (Recursive/Re-entry Prevention)
# This is placed AFTER sub-command routing to allow 'stop' and 'doctor'
# to be called from within an active session.
if [[ -n "$NEXUS_STATION_ACTIVE" ]] && [[ "$COMMAND_TYPE" != "audit" && "$COMMAND_TYPE" != "doctor" && "$COMMAND_TYPE" != "stop" ]]; then
    echo "[!] ERROR: Station already active in this shell." >&2
    exit 109
fi

if [[ -n "$TMUX" ]]; then
    CURRENT_SESSION=$(tmux display-message -p '#S' 2>/dev/null || echo "unknown")
    if [[ "$CURRENT_SESSION" == nexus_* ]]; then
        echo "[!] ERROR: Recursive Nexus detected. You are already inside '$CURRENT_SESSION'." >&2
        echo "    Opening a station from within a station is prohibited to prevent recursion." >&2
        exit 110
    fi
fi

# PREPEND NEXUS BIN TO PATH (Critical for isolated modules)
export PATH="$HOME/.nexus-shell/bin:$PATH"

if [[ ! -f "$FIRST_RUN_FLAG" ]] && [[ -z "$NEXUS_SKIP_FIRST_RUN" ]]; then
    echo "[*] First run detected. Launching setup wizard..."
    source "$NEXUS_KERNEL/boot/first_run.sh"
fi

# Python resolved earlier for daemon initiation.

# Profile and roles are now resolved via Python CapabilityRegistry during tool selection.

# 2.3 Dynamic Tool Resolution
get_tool_for_role() {
    local role="$1"
    "$Python_BIN" -c "
import sys, os
from pathlib import Path
sys.path.append(os.path.join(os.environ['NEXUS_HOME'], 'core'))
from engine.capabilities.registry import CapabilityRegistry
# Resolve Profile Path
profile = Path(os.path.expanduser('~/.nexus/profile.yaml'))
reg = CapabilityRegistry(profile)
print(reg.get_tool_for_role('$role'))
" 2>/dev/null || echo "zsh"
}

# 2.5 Path Utility
abspath() {
    [[ "$1" == /* ]] && echo "$1" || echo "$PWD/$1"
}

# 3. Environment Context
# 4. Identity & Configuration Defaults
# Axiom: Invariants first.
COMPOSITION="${NEXUS_COMPOSITION:-__saved_session__}"
PROFILE=""
WORKSPACE_MANIFEST=""
PROJECT_ARG=""

# 4.1 Positional Argument Parsing (Project vs Layout)
for arg in "$@"; do
    if [[ "$arg" != -* ]]; then
        if [[ "$arg" == *".nexus-workspace" ]]; then
            WORKSPACE_MANIFEST=$(abspath "$arg")
            break
        elif [[ -d "$arg" ]]; then
            PROJECT_ARG="$arg"
            break
        elif [[ "$COMPOSITION" == "__saved_session__" ]]; then
            # If it's not a dir and we haven't picked a layout, it might be the layout
            COMPOSITION="$arg"
        fi
    fi
done

if [[ -f "$WORKSPACE_MANIFEST" ]]; then
    echo "[*] Workspace Manifest Detected: $(basename "$WORKSPACE_MANIFEST")"
    PROJECT_ROOT=$(python3 -c "
import json, os
try:
    with open('$WORKSPACE_MANIFEST') as f:
        data = json.load(f)
        roots = data.get('roots', {})
        p_root = data.get('primary_root', '')
        # Improved Resolution: check if it's a key in roots first
        if p_root in roots:
            root = roots[p_root]
        elif p_root and not p_root.startswith('/'):
            root = os.path.join(os.path.dirname('$WORKSPACE_MANIFEST'), p_root)
        else:
            root = p_root
        print(os.path.abspath(os.path.expanduser(root)))
except: pass
")
    if [[ -z "${SESSION_ID:-}" ]]; then
        SESSION_ID=$(python3 -c "import json; print(json.load(open('$WORKSPACE_MANIFEST')).get('workspace_id', 'nexus-workspace'))" 2>/dev/null || echo "nexus-workspace")
    fi
else
    PROJECT_ROOT="${PROJECT_ARG:-$(pwd)}"
fi

PROJECT_ROOT=$(abspath "$PROJECT_ROOT")
if [[ -d "$PROJECT_ROOT" ]]; then
    PROJECT_ROOT="$(cd -- "$PROJECT_ROOT" && pwd)"
fi
export PROJECT_ROOT="$PROJECT_ROOT"
export WORKSPACE_MANIFEST="$WORKSPACE_MANIFEST"
export YAZI_CONFIG_HOME="$NEXUS_HOME/config/yazi"

if [[ -n "$WORKSPACE_MANIFEST" ]]; then
    PROJECT_NAME="${SESSION_ID}"
else
    PROJECT_NAME="$(basename "$PROJECT_ROOT")"
fi
export PROJECT_NAME="$PROJECT_NAME"
export NEXUS_PROJECT="$PROJECT_NAME"
export SESSION_ID="nexus_$PROJECT_NAME"
export SOCKET_LABEL="nexus_$PROJECT_NAME"

# Resolve Configuration Path
if [[ -f "$HOME/.config/nexus-shell/config/tmux/nexus.conf" ]]; then
    NEXUS_CONFIG_DIR="$HOME/.config/nexus-shell"
    TMUX_CONF="$NEXUS_CONFIG_DIR/config/tmux/nexus.conf"
else
    NEXUS_CONFIG_DIR="$NEXUS_HOME"
    TMUX_CONF="$NEXUS_CONFIG_DIR/config/tmux/nexus.conf"
fi

# Re-parse arguments for flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --composition|--layout|-l|-c) COMPOSITION="$2"; shift 2 ;;
        --profile|-p) PROFILE="$2"; shift 2 ;;
        *) shift ;; 
    esac
done

# Check if a saved session exists anywhere (Project Root or Fallback)
if [[ "$COMPOSITION" == "__saved_session__" || "$COMPOSITION" == "last" ]]; then
    HAS_SAVED=$("$Python_BIN" -c "
import sys, os
sys.path.append(os.path.join(os.environ['NEXUS_HOME'], 'core/engine/state'))
try:
    from state_engine import NexusStateEngine
    engine = NexusStateEngine(os.environ['PROJECT_ROOT'])
    windows = engine.get('session.windows')
    print('yes' if windows else 'no')
except: print('no')
")
    if [[ "$HAS_SAVED" == "no" ]]; then
        echo "    [*] No saved session found. Defaulting to vscodelike."
        COMPOSITION="vscodelike"
    else
        COMPOSITION="__saved_session__"
    fi
fi

# Detect Default Shell (Axiom: Deterministic Fallback)
if command -v zsh &>/dev/null; then
    NEXUS_SHELL="$(command -v zsh)"
else
    NEXUS_SHELL="$(command -v bash)"
fi
export NEXUS_SHELL

echo -e "\033[1;36m[*] INITIALIZING STATION: $PROJECT_NAME\033[0m"
echo "    Layout: $COMPOSITION"
echo "    Session: $SESSION_ID"

# Tool resolution is now deferred to the CapabilityRegistry.
ROUTER_BIN="$NEXUS_KERNEL/exec/router.sh"

# Build isolated state directory
export PX_STATE_DIR="/tmp/nexus_$(whoami)/$PROJECT_NAME/parallax"
mkdir -p "$PX_STATE_DIR"

# 5. Mandatory State Reset & Initialization
# DISCOVERY: Do not kill-server. We want multi-window support.
STATION_EXISTS=$(tmux -L "$SOCKET_LABEL" has-session -t "$SESSION_ID" 2>/dev/null && echo "yes" || echo "no")

# Initialize Kernel State
"$NEXUS_ENGINE/api/station_manager.sh" "$PROJECT_NAME" init

if [[ "$STATION_EXISTS" == "yes" ]]; then
    # Axiom: Idempotent Window Recovery
    # First, check if a window with this workspace name already exists
    TARGET_WINDOW_NAME="workspace_0"
    W0_EXISTS=$(tmux -L "$SOCKET_LABEL" list-windows -t "$SESSION_ID" -F '#W' | grep -q "^$TARGET_WINDOW_NAME$" && echo "yes" || echo "no")
    
    if [[ "$W0_EXISTS" == "yes" ]]; then
        echo "[*] Reusing existing workspace window: 0"
        WINDOW_IDX=0
    else
        # Find the lowest available window index
        MAX_WINDOWS=10
        WINDOW_IDX=-1
        USED_WINDOWS=$(tmux -L "$SOCKET_LABEL" list-windows -t "$SESSION_ID" -F '#{window_index}')
        for ((i=0; i<MAX_WINDOWS; i++)); do
            if ! echo "$USED_WINDOWS" | grep -q "^$i$"; then
                WINDOW_IDX=$i
                break
            fi
        done
        
        if [[ $WINDOW_IDX -eq -1 ]]; then
             echo "[!] CRITICAL: Window limit reached." >&2
             exit 112
        fi
        echo "    [*] Opening new window slot: $WINDOW_IDX"
        tmux -L "$SOCKET_LABEL" new-window -d -t "$SESSION_ID" -k -t "$WINDOW_IDX" -n "workspace_$WINDOW_IDX" -c "$PROJECT_ROOT" "$NEXUS_SHELL"
    fi
    
    # Generate client session
    CLIENT_SESSION="${SESSION_ID}_client_$$"
    tmux -L "$SOCKET_LABEL" new-session -d -t "$SESSION_ID" -s "$CLIENT_SESSION"
    
else
    echo "[*] Initializing Station Core..."
    WINDOW_IDX=0
    
    # === AXIOM: NEGATIVE SPACE INVARIANTS ===
    # V-01: Tmux Binary Health
    TMUX_BIN=$(command -v tmux) || { echo "[!] CRITICAL: tmux not found in PATH." >&2; exit 113; }
    
    # V-02: Socket Writability
    # We use a project-specific socket label to bypass global corruption.
    SOCKET_LABEL="nexus_$PROJECT_NAME"
    
    # V-04: Project Root Integrity
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        echo "[!] CRITICAL: Project root does not exist: $PROJECT_ROOT" >&2
        exit 114
    fi
    
    # Axiom: Dynamic Terminal Invariants
    COLS=$(tput cols 2>/dev/null || echo 80)
    LINES=$(tput lines 2>/dev/null || echo 24)
    
    # Create the root session and window 0
    # Use -L for socket isolation and capture all stderr for diagnosis
    TMUX_ERR=$(tmux -L "$SOCKET_LABEL" -f "$TMUX_CONF" new-session -d -s "$SESSION_ID" -n "workspace_0" -c "$PROJECT_ROOT" -x "$COLS" -y "$LINES" "$NEXUS_SHELL" 2>&1) || {
        echo -e "\033[1;31m[!] CRITICAL: Tmux failed to initialize session '$SESSION_ID'\033[0m" >&2
        echo "    Reason: $TMUX_ERR" >&2
        echo "    Socket Label: $SOCKET_LABEL" >&2
        echo "    Config: $TMUX_CONF" >&2
        echo "    Root: $PROJECT_ROOT" >&2
        exit 1
    }
    
    # --- MULTI-WINDOW RESTORE ---
    # Detect all window indices via State Engine (Fallback-Aware)
    if [[ "$COMPOSITION" == "__saved_session__" || "$COMPOSITION" == "last" ]]; then
        SAVED_WINDOWS=$("$Python_BIN" -c "
import sys, os
sys.path.append(os.path.join(os.environ['NEXUS_HOME'], 'core/engine/state'))
try:
    from state_engine import NexusStateEngine
    engine = NexusStateEngine(os.environ['PROJECT_ROOT'])
    windows = engine.get('session.windows')
    if windows:
        print(' '.join(sorted(windows.keys(), key=int)))
except: pass
")
        if [[ -n "$SAVED_WINDOWS" ]]; then
            echo "    [*] Detected multi-window state: $SAVED_WINDOWS"
            for W_IDX in $SAVED_WINDOWS; do
                if [[ "$W_IDX" != "0" ]]; then
                    echo "    [*] Recreating window slot $W_IDX..."
                    tmux -L "$SOCKET_LABEL" new-window -d -t "$SESSION_ID:$W_IDX" -n "workspace_$W_IDX" -c "$PROJECT_ROOT" "$NEXUS_SHELL"
                fi
            done
        fi
    fi

    # Generate the first client session
    CLIENT_SESSION="${SESSION_ID}_client_$$"
    tmux -L "$SOCKET_LABEL" new-session -d -t "$SESSION_ID" -s "$CLIENT_SESSION"
fi

# --- Window-Specific Tool Configuration ---
export WINDOW_IDX="$WINDOW_IDX"
export NEXUS_WINDOW_SUFFIX="_w$WINDOW_IDX"
export NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}${NEXUS_WINDOW_SUFFIX}.pipe"
mkdir -p "$(dirname "$NVIM_PIPE")"
export EDITOR_CMD="$NEXUS_EDITOR"
[[ "$NEXUS_EDITOR" == *"nvim"* ]] && export EDITOR_CMD="$NEXUS_EDITOR --listen $NVIM_PIPE"
export NEXUS_MENU_CMD="PX_STATE_DIR=$PX_STATE_DIR $NEXUS_MENU"
HAS_FILES=true

CLIENT_SESSION="${CLIENT_SESSION}"
# --- Environment Propagation for Subprocesses ---
export NEXUS_WINDOW_SUFFIX
export NVIM_PIPE

# --- Graceful Termination & Cleanup ---
# We track subprocesses to kill them on exit
cleanup() {
    echo -e "\n\033[1;33m[*] Nexus Shutdown in progress...\033[0m"
    # Kill background bridges/services
    pkill -P $$ 2>/dev/null || true
    # Stop Boot Services
    [[ -f "$NEXUS_KERNEL/boot/boot_loader.sh" ]] && "$NEXUS_KERNEL/boot/boot_loader.sh" stop
    # Remove window-specific pipes
    rm -f "$NVIM_PIPE" 2>/dev/null
    
    # 1. Kill Event Bus Server if it was started by this session
    if [[ -n "$NEXUS_BUS_PID" ]]; then
        echo "[*] Stopping Event Bus & AI Daemon..."
        kill "$NEXUS_SID_PID" 2>/dev/null || true
        kill "$NEXUS_BUS_PID" 2>/dev/null || true
    fi
    
    # 2. Cleanup Virtual Workspace
    rm -rf "/tmp/nexus/workspaces/$SESSION_ID" 2>/dev/null || true
    
    echo "[*] Cleanup complete."
}
trap cleanup EXIT SIGINT SIGTERM
# PHASE 0 & 5: (Services now started via Python ensure_alive)

# Services are now managed via Python ensure_alive

if ! tmux -L "$SOCKET_LABEL" has-session -t "$SESSION_ID:HUD" 2>/dev/null; then
    tmux -L "$SOCKET_LABEL" new-window -d -t "$SESSION_ID:10" -n "HUD" -c "$PROJECT_ROOT" "$NEXUS_HOME/core/ui/hud/renderer.sh"
fi

rm -rf "/tmp/nexus_$(whoami)/$PROJECT_NAME/pipes"
mkdir -p "/tmp/nexus_$(whoami)/$PROJECT_NAME/pipes"
# sleep 0.5 # Reduced sleep

# 6. (Replaced by earlier atomic creation block)

# The environment for these tools is now managed by the WorkspaceOrchestrator in Python.

# PHASE 9: Build the Layout (Orchestration V3)
echo "[*] Constructing Workspace: $COMPOSITION in Slot $WINDOW_IDX..."
sleep 0.2 # Brief sync to ensure tmux session is fully registered
"$Python_BIN" "$NEXUS_ENGINE/lib/daemon_client.py" boot_layout "{\"name\": \"$COMPOSITION\", \"window\": \"$SESSION_ID:$WINDOW_IDX\", \"project_root\": \"$PROJECT_ROOT\", \"socket_label\": \"$SOCKET_LABEL\"}"

# Success Handover
echo -e "\033[1;32m[*] Station Solidified. Attaching...\033[0m"
export NEXUS_STATION_ACTIVE=1
tmux -L "$SOCKET_LABEL" select-window -t "$CLIENT_SESSION:$WINDOW_IDX"
tmux -L "$SOCKET_LABEL" attach-session -t "$CLIENT_SESSION"
