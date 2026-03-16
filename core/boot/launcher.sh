#!/bin/bash
# --- Nexus Supervisor: SIMPLIFIED ROBUST EDITION ---
# Enforces stability through "Session-First" logic.

set -e

# 0. Early State Cleanup (Before any session checks)
# This ensures a clean slate for critical components like the nvim pipe.
# Note: NEXUS_STATE is not yet defined, so we use the explicit path.
rm -rf "/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}.pipe" 2>/dev/null

# 1. Identity Guard (Recursive/Re-entry Prevention)
if [[ -n "$NEXUS_STATION_ACTIVE" ]]; then
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

# 1.1 Process Genealogy Guard (Detect nested nxs calls)
if [[ -n "$NEXUS_BOOT_IN_PROGRESS" ]]; then
    echo "[!] ERROR: Circular boot detected. Aborting." >&2
    exit 111
fi
export NEXUS_BOOT_IN_PROGRESS=1

# 2. Physical Path Resolution (Follow symlinks to find Nexus Home)
REAL_PATH="$0"
while [ -h "$REAL_PATH" ]; do
    DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"
    REAL_PATH="$(readlink "$REAL_PATH")"
    [[ $REAL_PATH != /* ]] && REAL_PATH="$DIR/$REAL_PATH"
done
# SCRIPT_DIR is .../nexus-shell/core/boot
SCRIPT_DIR="$(cd -P "$(dirname "$REAL_PATH")" && pwd)"
export NEXUS_HOME="$(cd "$SCRIPT_DIR/../../" && pwd)"
export NEXUS_CORE="$NEXUS_HOME/core"
export NEXUS_SCRIPTS="$NEXUS_CORE/boot"

# PREPEND NEXUS BIN TO PATH (Critical for isolated modules)
export PATH="$HOME/.nexus-shell/bin:$PATH"

# 2.5 Path Utility
abspath() {
    [[ "$1" == /* ]] && echo "$1" || echo "$PWD/$1"
}

# 3. Environment Context
# Identify Project Root or Workspace Manifest Early
WORKSPACE_MANIFEST=""
PROJECT_ARG=""
for arg in "$@"; do
    if [[ "$arg" != -* ]]; then
        if [[ "$arg" == *".nexus-workspace" ]]; then
            WORKSPACE_MANIFEST=$(abspath "$arg")
        else
            PROJECT_ARG="$arg"
        fi
        break
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

# 4. Tiered Configuration Loading (Clean Slate V1)
echo "[*] Loading Workspace Configuration..."
# Resolve Python Binary
[[ -x "$NEXUS_HOME/.venv/bin/python3" ]] && Python_BIN="$NEXUS_HOME/.venv/bin/python3" \
|| [[ -x "$Python_BIN" ]] && Python_BIN="$Python_BIN" \
|| Python_BIN="python3"

eval "$("$Python_BIN" "$NEXUS_CORE/api/config_helper.py")"

# Axiom Note: Saved session detection moved to final stage (P-05)
COMPOSITION="${NEXUS_COMPOSITION:-__saved_session__}"
PROFILE=""

# Re-parse arguments for flags
set -- "${@}"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --composition|--layout|-l|-c) 
            COMPOSITION="$2"
            shift 2 ;;
        --profile|-p)
            PROFILE="$2"
            shift 2 ;;
        --list)
            echo -e "\033[1;36m[*] Available Layouts (Compositions):\033[0m"
            ls "$NEXUS_HOME/core/compositions"/*.json | xargs -n 1 basename | sed 's/\.json//' | awk '{print "  - " $1}'
            echo -e "\n\033[1;36m[*] Available Profiles:\033[0m"
            ls "$NEXUS_HOME/config/profiles"/*.yaml | xargs -n 1 basename | sed 's/\.yaml//' | awk '{print "  - " $1}'
            exit 0 ;;
        --debug|-d)
            export NEXUS_DEBUG=1
            set -x
            shift ;;
        *) shift ;; 
    esac
done

# Load Profile if specified
if [[ -n "$PROFILE" ]]; then
    if [[ -f "$NEXUS_CORE/env/profile_loader.sh" ]]; then
        source "$NEXUS_CORE/env/profile_loader.sh"
        load_profile "$PROFILE"
        # Profile might override composition
        [[ -n "$NEXUS_COMPOSITION" ]] && COMPOSITION="$NEXUS_COMPOSITION"
    else
        echo "[!] Warning: Profile loader not found at $NEXUS_CORE/env/profile_loader.sh" >&2
    fi
fi

SESSION_ID="nexus_$PROJECT_NAME"

# Resolve Configuration Path (Detect Layout)
if [[ -f "$HOME/.config/nexus-shell/config/keybinds.conf" ]]; then
    NEXUS_CONFIG_DIR="$HOME/.config/nexus-shell"
    TMUX_CONF="$NEXUS_CONFIG_DIR/tmux/nexus.conf"
else
    NEXUS_CONFIG_DIR="$NEXUS_HOME"
    TMUX_CONF="$NEXUS_CONFIG_DIR/config/tmux/nexus.conf"
fi

echo -e "\033[1;36m[*] INITIALIZING STATION: $PROJECT_NAME\033[0m"
echo "    Layout: $COMPOSITION"
echo "    Session: $SESSION_ID"

# 4.5 Load Legacy tools.conf (Backwards Compatibility)
# Priority: 1. Workspace Flags 2. .nexus.yaml 3. tools.conf 4. Internal Defaults
TOOLS_CONF="$NEXUS_CONFIG_DIR/tools.conf"
# Dev mode fallback: if not in .config, check NEXUS_HOME/config/tools.conf
if [[ ! -f "$TOOLS_CONF" ]]; then
    TOOLS_CONF="$NEXUS_HOME/config/tools.conf"
fi

if [[ -f "$TOOLS_CONF" ]]; then
    # We source it AFTER config_helper.py to ensure user manually edited configs win
    source "$TOOLS_CONF"
fi

# Apply Tool Defaults (Configuration Hierarchy)
# Handled by config_helper.py (Sovereign Authority)
export NEXUS_EDITOR="${NEXUS_EDITOR:-nvim}"
export NEXUS_FILES="${NEXUS_FILES:-yazi}"
export NEXUS_CHAT="${NEXUS_CHAT:-opencode}"
export NEXUS_MENU="${NEXUS_MENU:-$NEXUS_HOME/modules/menu/bin/nexus-menu}"
export NEXUS_TERMINAL="${NEXUS_TERMINAL:-/bin/zsh -i}"
ROUTER_BIN="$NEXUS_CORE/exec/router.sh"

# Build isolated state directory
export NEXUS_STATE_DIR="/tmp/nexus_$(whoami)/$PROJECT_NAME/state"
mkdir -p "$NEXUS_STATE_DIR"

# 5. Mandatory State Reset & Initialization
# DISCOVERY: Do not kill-server. We want multi-window support.
STATION_EXISTS=$(tmux has-session -t "$SESSION_ID" 2>/dev/null && echo "yes" || echo "no")

# Initialize Kernel State
"$NEXUS_CORE/api/station_manager.sh" "$PROJECT_NAME" init

if [[ "$STATION_EXISTS" == "yes" ]]; then
    echo "[*] Station already exists for $PROJECT_NAME."
    
    # 1. Find the lowest available window index (0-9)
    MAX_WINDOWS=10
    WINDOW_IDX=-1
    
    # Build a string of currently used window indices
    USED_WINDOWS=$(tmux list-windows -t "$SESSION_ID" -F '#{window_index}')
    
    for ((i=1; i<MAX_WINDOWS; i++)); do
        if ! echo "$USED_WINDOWS" | grep -q "^$i$"; then
            WINDOW_IDX=$i
            break
        fi
    done
    
    if [[ $WINDOW_IDX -eq -1 ]]; then
         echo "[!] CRITICAL: Window limit ($MAX_WINDOWS) reached for this project." >&2
         exit 112
    fi
  # --- Sovereign Stack Bindings ---
tmux bind-key -n M-n run-shell "$NEXUS_CORE/stack/nxs-stack next \"#{q:@nexus_role}\""
tmux bind-key -n M-p run-shell "$NEXUS_CORE/stack/nxs-stack prev \"#{q:@nexus_role}\""
tmux bind-key -n M-d run-shell "$NEXUS_CORE/stack/nxs-stack delete \"#{q:@nexus_role}\""

# --- Live Preview (Cmd-Shift-V behavior) ---
# Queries Nvim for current file and pushes to renderer stack
tmux bind-key -n M-v run-shell "FILE=\$(nvim --server \"\$NVIM_PIPE\" --remote-expr \"expand('%:p')\" 2>/dev/null); if [[ -n \"\$FILE\" ]]; then $NEXUS_CORE/stack/nxs-stack push \"renderer\" \"$NEXUS_CORE/view/nxs-view '\$FILE'\" \"Preview: \$(basename \"\$FILE\")\"; fi"

    echo "    [*] Opening new window slot: $WINDOW_IDX"
    tmux new-window -d -t "$SESSION_ID:$WINDOW_IDX" -n "workspace_$WINDOW_IDX" -c "$PROJECT_ROOT" "/bin/zsh"
    
    # Generate a unique client session ID so this terminal can view a different window than the first terminal
    CLIENT_SESSION="${SESSION_ID}_client_$$"
    tmux new-session -d -t "$SESSION_ID" -s "$CLIENT_SESSION"
    
else
    echo "[*] Initializing Station Core..."
    WINDOW_IDX=0
    # Create the root session and window 0
    tmux -f "$TMUX_CONF" new-session -d -s "$SESSION_ID" -n "workspace_0" -c "$PROJECT_ROOT" -x "$(tput cols)" -y "$(tput lines)" "/bin/zsh"
    
    # --- MULTI-WINDOW RESTORE ---
    # If restoring a saved session, detect all window indices in the State Engine
    # Axiom Fix: Use absolute PROJECT_ROOT path (I-04)
    if [[ "$COMPOSITION" == "__saved_session__" || "$COMPOSITION" == "last" ]]; then
        STATE_FILE="$PROJECT_ROOT/.nexus/state.json"
        if [[ -f "$STATE_FILE" ]]; then
            SAVED_WINDOWS=$("$Python_BIN" -c "
import json, os
try:
    with open('$STATE_FILE') as f:
        data = json.load(f)
        indices = [k.split('.')[-1] for k in data.keys() if k.startswith('session.windows.')]
        print(' '.join(sorted(indices, key=int)))
except: pass
")
            if [[ -n "$SAVED_WINDOWS" ]]; then
                echo "    [*] Detected multi-window state: $SAVED_WINDOWS"
                for W_IDX in $SAVED_WINDOWS; do
                    if [[ "$W_IDX" != "0" ]]; then
                        echo "    [*] Recreating window slot $W_IDX..."
                        # Ensure window is created in its original root context if possible (future enhancement T-7 handles cd)
                        tmux new-window -d -t "$SESSION_ID:$W_IDX" -n "workspace_$W_IDX" -c "$PROJECT_ROOT" "/bin/zsh"
                    fi
                done
            fi
        fi
    fi

    # Generate the first client session
    CLIENT_SESSION="${SESSION_ID}_client_$$"
    tmux new-session -d -t "$SESSION_ID" -s "$CLIENT_SESSION"
fi

# --- Window-Specific Tool Configuration ---
export WINDOW_IDX="$WINDOW_IDX"
export NEXUS_WINDOW_SUFFIX="_w$WINDOW_IDX"
export NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}${NEXUS_WINDOW_SUFFIX}.pipe"
mkdir -p "$(dirname "$NVIM_PIPE")"
export EDITOR_CMD="$NEXUS_EDITOR"
[[ "$NEXUS_EDITOR" == *"nvim"* ]] && export EDITOR_CMD="$NEXUS_EDITOR --listen $NVIM_PIPE"
export PARALLAX_CMD="PX_STATE_DIR=$PX_STATE_DIR $NEXUS_MENU"
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
    [[ -f "$NEXUS_CORE/boot/boot_loader.sh" ]] && "$NEXUS_CORE/boot/boot_loader.sh" stop
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
# PHASE 4: Core Orchestration (HUD & Services)
if [[ -f "$NEXUS_HOME/core/services/hud_service.sh" ]]; then
    "$NEXUS_HOME/core/services/hud_service.sh" start
fi

# Agent Follower Bridge (Ghosting)
if [[ "$NEXUS_FOLLOW_MODE" == "true" ]]; then
    echo "[*] Starting Agent Follower Bridge..."
    "$NEXUS_HOME/core/services/follower_bridge.sh" &
    export NEXUS_BRIDGE_PID=$!
fi

# PHASE 0: Event Bus (Nervous System)
# Start the event server in the background
echo "[*] Starting Nexus Event Bus..."
export NEXUS_BUS_LOG="/tmp/nexus_$(whoami)/$PROJECT_NAME/bus.log"
"$Python_BIN" "$NEXUS_CORE/bus/event_server.py" > "$NEXUS_BUS_LOG" 2>&1 &
export NEXUS_BUS_PID=$!
# Wait for socket
for i in {1..10}; do
    [[ -S "/tmp/nexus_$(whoami)/$PROJECT_NAME/bus.sock" ]] && break
    sleep 0.1
done

# Start Sovereign Intelligence Daemon (SID)
if [[ -f "$NEXUS_CORE/ai/sid.py" ]]; then
    echo "[*] Starting Sovereign Intelligence Daemon (SID)..."
    export NEXUS_SID_LOG="/tmp/nexus_$(whoami)/$PROJECT_NAME/sid.log"
    "$Python_BIN" "$NEXUS_CORE/ai/sid.py" > "$NEXUS_SID_LOG" 2>&1 &
    export NEXUS_SID_PID=$!
fi

# PHASE 5: Boot Sequence
if [[ -f "$NEXUS_CORE/boot/boot_loader.sh" ]]; then
    echo "[*] Launching Boot Services..."
    "$NEXUS_CORE/boot/boot_loader.sh" start
fi

if ! tmux has-session -t "$SESSION_ID:HUD" 2>/dev/null; then
    tmux new-window -d -t "$SESSION_ID:10" -n "HUD" -c "$PROJECT_ROOT" "$NEXUS_HOME/core/hud/renderer.sh"
fi

if [[ "$NEXUS_DEBUG" == "1" ]]; then
    if ! tmux has-session -t "$SESSION_ID:DEBUG" 2>/dev/null; then
        tmux new-window -d -t "$SESSION_ID:11" -n "DEBUG" -c "$PROJECT_ROOT" "$NEXUS_HOME/core/boot/debug_tail.sh"
    fi
fi

rm -rf "/tmp/nexus_$(whoami)/$PROJECT_NAME/pipes"
mkdir -p "/tmp/nexus_$(whoami)/$PROJECT_NAME/pipes"
# sleep 0.5 # Reduced sleep

# 6. (Replaced by earlier atomic creation block)

# 7. Global Server Options
tmux set-option -gs exit-empty on
tmux set-option -gs exit-unattached off # We still want to allow detaching without killing, but exit-empty handles the 'no sessions' case

# 8. Propagate Environment to Server (Global)
tmux set-environment -g NEXUS_HOME "$NEXUS_HOME"
tmux set-environment -g NEXUS_CORE "$NEXUS_CORE"
tmux set-environment -g NEXUS_BOOT "$NEXUS_CORE/boot"
tmux set-environment -g NEXUS_SCRIPTS "$NEXUS_CORE/boot"
tmux set-environment -g PROJECT_ROOT "$PROJECT_ROOT"

# --- Sovereign Workspace Setup ---
if [[ -f "$NEXUS_HOME/core/lib/workspace_manager.sh" ]]; then
    source "$NEXUS_HOME/core/lib/workspace_manager.sh"
    setup_workspace "$WORKSPACE_MANIFEST"
    export VIRTUAL_ROOT=$(get_virtual_root)
    tmux set-environment -g VIRTUAL_ROOT "$VIRTUAL_ROOT"
fi

# Propagate Environment to Session (Local)
tmux set-environment -t "$SESSION_ID" NEXUS_STATION_ACTIVE 1
tmux set-environment -t "$SESSION_ID" NEXUS_PROJECT "$PROJECT_NAME"
# Globalize for all panes
tmux set-environment -g WORKSPACE_MANIFEST "$WORKSPACE_MANIFEST"
tmux set-environment -g YAZI_CONFIG_HOME "$YAZI_CONFIG_HOME"
tmux set-environment -g NVIM_PIPE "$NVIM_PIPE"
tmux set-environment -g PROJECT_ROOT "$PROJECT_ROOT"

# ANTI-GHOSTING: Force status bar sanity
tmux set-option -g status on
tmux set-option -g status-position top
tmux set-environment -g @nexus_mode ""

tmux set-environment -t "$SESSION_ID" NEXUS_CONFIG "$NEXUS_CONFIG_DIR"
tmux set-environment -t "$SESSION_ID" EDITOR_CMD "$EDITOR_CMD"
tmux set-environment -t "$SESSION_ID" PARALLAX_CMD "$PARALLAX_CMD"
tmux set-environment -t "$SESSION_ID" NEXUS_FILES "$NEXUS_FILES"
tmux set-environment -t "$SESSION_ID" NEXUS_CHAT "$NEXUS_CHAT"

# 9. Build the Layout (Synchronous & Staggered)
if [[ "$COMPOSITION" == "__saved_session__" && "$STATION_EXISTS" == "no" ]]; then
    # Full Session Restore: Build all windows
    CURRENT_WINDOWS=$(tmux list-windows -t "$SESSION_ID" -F '#{window_index}')
    for W_I in $CURRENT_WINDOWS; do
        echo "[*] Building Station Architecture in Slot $W_I..."
        # Axiom Authority Invariant (P-05)
        # Final check: if state exists for THIS window, force saved session mode
        W_COMP="$COMPOSITION"
        if [[ -f "$PROJECT_ROOT/.nexus/state.json" ]]; then
             if "$Python_BIN" -c "import json, sys; d=json.load(open('$PROJECT_ROOT/.nexus/state.json')); sys.exit(0 if 'session' in d and 'windows' in d['session'] and '$W_I' in d['session']['windows'] else 1)" 2>/dev/null; then
                 W_COMP="__saved_session__"
              fi
        fi

        # We must re-export window-specific variables for the layout engine
        export WINDOW_IDX="$W_I"
        export NEXUS_WINDOW_SUFFIX="_w$W_I"
        export NVIM_PIPE="/tmp/nexus_$(whoami)/pipes/nvim_${PROJECT_NAME}${NEXUS_WINDOW_SUFFIX}.pipe"
        "$NEXUS_CORE/layout/layout_engine.sh" "$SESSION_ID:$W_I" "$W_COMP" "$SESSION_ID" "$PROJECT_ROOT"
    done
else
    # Standard Case: Build only the targeted window
    echo "[*] Building Station Architecture in Slot $WINDOW_IDX..."

    # Execute the architecture build
    "$NEXUS_CORE/layout/layout_engine.sh" "$SESSION_ID:$WINDOW_IDX" "$COMPOSITION" "$SESSION_ID" "$PROJECT_ROOT"
fi

# Restore active theme from persistent state
if [[ -x "$NEXUS_SCRIPTS/theme.sh" ]]; then
    CURRENT_THEME=$("$NEXUS_SCRIPTS/theme.sh" current)
    "$NEXUS_SCRIPTS/theme.sh" apply "$CURRENT_THEME" >/dev/null 2>&1 || true
fi

# 10. Success Handover
echo -e "\033[1;32m[*] Station Solidified. Attaching...\033[0m"
export NEXUS_STATION_ACTIVE=1

# Assertion: Terminal Lifecycle Invariant (Negative Space)
# The station MUST NOT exist without an active observer (terminal window).
# We anchor the session's life to the client's attachment state.
# tmux set-hook -t "$SESSION_ID" client-detached "kill-session -t '$SESSION_ID'"
# Ensure the client session focuses the window we just built
tmux select-window -t "$CLIENT_SESSION:$WINDOW_IDX"

tmux attach-session -t "$CLIENT_SESSION"
