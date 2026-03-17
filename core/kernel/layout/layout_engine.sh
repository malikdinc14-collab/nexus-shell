#!/bin/bash
# layout_engine.sh - Staggered Synchronous Architect
# V4: Pane-ID Tracking (Index Independent)


nxs_assert() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo -e "\n\033[1;31m[!] ARCHITECT ERROR: $1\033[0m" >&2
        tmux list-panes -F "ID:#{pane_id} IDX:#{pane_index} [#{pane_width}x#{pane_height}]" >&2
        exit 1
    fi
}

build_vscodelike() {
    local WINDOW_ID="$1"
    local PROJECT_ROOT="$2"
    local STAGGER="sleep 0.1"
    
    echo "    [*] Initializing PTY Handshake..."
    sleep 0.5 # Wait for terminal resize stabilization

    # Capture the initial Center Pane ID
    local CENTER_PANE=$(tmux display-message -p '#{pane_id}')
    
    # 1. TREE (Left)
    echo "    [*] Carving Sidebars..."
    
    # Multi-Root Hub: Launch Yazi with multiple tabs if workspace manifest exists
    local -a EXPLORER_ARGS
    EXPLORER_ARGS+=( "$PROJECT_ROOT" ) 
    local ROOTS_ENV=""
    local CWD_ARG="-c \"$PROJECT_ROOT\""
    
    # Check for manifest globally or locally
    local MANIFEST="${WORKSPACE_MANIFEST:-$NEXUS_WORKSPACE_MANIFEST}"

    if [[ -f "$MANIFEST" ]]; then
        source "$NEXUS_HOME/core/engine/lib/workspace_manager.sh"
        # get_workspace_roots returns newline-separated paths
        local RAW_ROOTS=$(get_workspace_roots "$MANIFEST")
        
        # Build arguments list robustly using a while loop and null-safe reading
        EXPLORER_ARGS=()
        while IFS= read -r line; do
            [[ -n "$line" ]] && EXPLORER_ARGS+=( "$line" )
        done <<< "$RAW_ROOTS"
        
        # Build PIPE-separated roots for the lua plugin (handles spaces)
        local ROOTS_LIST=$(printf "%s|" "${EXPLORER_ARGS[@]}")
        ROOTS_ENV="-e NEXUS_WORKSPACE_ROOTS='${ROOTS_LIST%|}'"
        
        # CRITICAL: Start in neutral zone to prevent auto-opening a duplicate tab for PROJECT_ROOT
        CWD_ARG="-c /tmp" 
    fi

    # Build the final command string with properly escaped arguments
    local ARGS_STRING=""
    for arg in "${EXPLORER_ARGS[@]}"; do
        # Use printf %q to safely escape the path for the shell inside tmux
        local escaped_arg=$(printf "%q" "$arg")
        ARGS_STRING="$ARGS_STRING $escaped_arg"
    done

    # Explicitly pass YAZI_CONFIG_HOME to the split-window environment
    local ENV_ARGS="$ROOTS_ENV -e YAZI_CONFIG_HOME='$YAZI_CONFIG_HOME' -e NEXUS_HOME='$NEXUS_HOME'"

    local CMD="tmux split-window $ENV_ARGS $CWD_ARG -h -b -l 30 -t \"$CENTER_PANE\" \"$WRAPPER $NEXUS_FILES $ARGS_STRING\""
    eval "$CMD"
    
    local TREE_PANE=$(tmux display-message -p '#{pane_id}')
    tmux set-option -p -t "$TREE_PANE" @nexus_role "files"
    nxs_assert "Tree Split"
    $STAGGER
    
    # 2. CHAT (Right)
    tmux split-window -h -l 45 -t "$CENTER_PANE" -c "$PROJECT_ROOT" "$WRAPPER /bin/zsh"
    local CHAT_PANE=$(tmux display-message -p '#{pane_id}')
    nxs_assert "Chat Split"
    $STAGGER
    
    # 3. UI (Bottom of Chat)
    tmux split-window -v -p 25 -t "$CHAT_PANE" -c "$PROJECT_ROOT" "$WRAPPER $BRIDGE/transaction_ui.sh"
    nxs_assert "UI Split"
    $STAGGER
    
    # 4. PARALLAX (Top of Center)
    echo "    [*] Carving Center-Shell..."
    tmux split-window -v -b -l 8 -t "$CENTER_PANE" -c "$PROJECT_ROOT" "$WRAPPER $PARALLAX_CMD"
    local MENU_PANE=$(tmux display-message -p '#{pane_id}')
    tmux set-option -p -t "$MENU_PANE" @nexus_role "menu"
    nxs_assert "Parallax Split"
    $STAGGER
    
    # 5. TERMINAL (Bottom of Center)
    tmux split-window -v -l 12 -t "$CENTER_PANE" -c "$PROJECT_ROOT" "$WRAPPER /bin/zsh -i"
    local TERM_PANE=$(tmux display-message -p '#{pane_id}')
    nxs_assert "Terminal Split"
    $STAGGER
    
    # 6. TRACE (Right of Terminal)
    tmux split-window -h -p 35 -t "$TERM_PANE" -c "$PROJECT_ROOT" "$WRAPPER tail -f /tmp/px-agent-trace.log"
    nxs_assert "Trace Split"
    
    # Final Step: Launch Editor in the remaining Center space
    echo "    [*] Solidifying Editor Core..."
    tmux send-keys -t "$CENTER_PANE" "$WRAPPER $EDITOR_CMD" Enter
    tmux set-option -p -t "$CENTER_PANE" @nexus_role "editor"
    nxs_assert "Editor Initiation"
    
    # --- Slot Invariant Anchoring ---
    # Assign sequential Slot numbers in visual order (top-left to bottom-right)
    local i=1
    for p in $(tmux list-panes -t "$WINDOW_ID" -F '#{pane_id}'); do
        tmux set-option -p -t "$p" @nexus_slot "$i"
        ((i++))
    done

    # Set titles and focus
    tmux select-pane -t "$CENTER_PANE" -T "editor"
    tmux select-pane -t "$TERM_PANE" -T "terminal"
    tmux select-pane -t "$TERM_PANE"
}

# --- Entry Point ---
# SCRIPT_DIR is .../nexus-shell/core/kernel/layout
SCRIPT_DIR="$(cd -P "$(dirname "$0")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"
export NEXUS_CORE="${NEXUS_CORE:-$NEXUS_HOME/core}"
export WRAPPER="$NEXUS_CORE/boot/pane_wrapper.sh"
export BRIDGE="$NEXUS_CORE/bridge"

WINDOW_ID="$1"
LAYOUT="$2"
SESSION_ID="$3"
export PROJECT_ROOT="$4"

echo "    [*] Seeking Composition: $LAYOUT"

# 0. Saved session restore
if [[ "$LAYOUT" == "__saved_session__" ]]; then
    WINDOW_IDX="${WINDOW_ID#*:}"
    STATE_ENGINE="$NEXUS_CORE/state/state_engine.sh"
    
    # Check State Engine for session data
    SAVED_LAYOUT=$("$STATE_ENGINE" get "session.windows.$WINDOW_IDX")
    
    if [[ -n "$SAVED_LAYOUT" && "$SAVED_LAYOUT" != "{}" && "$SAVED_LAYOUT" != "null" ]]; then
        echo "    [*] Restoring layout for window $WINDOW_IDX from State Engine..."
        export STATE_JSON="$SAVED_LAYOUT"
        "$SCRIPT_DIR/restore_layout.sh" "$WINDOW_ID" "" "$PROJECT_ROOT"
        exit $?
    fi

    # Fallback to legacy branch-specific files
    GIT_BRANCH=$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null || echo "main")
    SAFE_BRANCH="${GIT_BRANCH//\//_}"
    STATE_FILE="$PROJECT_ROOT/.nexus/branches/$SAFE_BRANCH/window_$WINDOW_IDX.json"
    
    if [[ -f "$STATE_FILE" ]]; then
        echo "    [*] Restoring legacy layout for window $WINDOW_IDX from $STATE_FILE..."
        export STATE_JSON=$(cat "$STATE_FILE")
        "$SCRIPT_DIR/restore_layout.sh" "$WINDOW_ID" "" "$PROJECT_ROOT"
        exit $?
    else
        echo "    [!] No saved state found, loading default composition."
        LAYOUT="vscodelike"
    fi
fi


# 1. Check for JSON Composition
# Support absolute paths (e.g. from .nexus/compositions/saved.json)
if [[ "$LAYOUT" == /* && -f "$LAYOUT" ]]; then
    COMP_JSON="$LAYOUT"
else
    COMP_JSON="$NEXUS_HOME/core/ui/compositions/$LAYOUT.json"
    # Also check project-local compositions
    if [[ ! -f "$COMP_JSON" ]]; then
        COMP_JSON="$PROJECT_ROOT/.nexus/compositions/$LAYOUT.json"
    fi
fi

if [[ -f "$COMP_JSON" ]]; then
    echo "    [*] Applying Data-Driven Composition..."
    
    # NEW: Detect Momentum Snapshot type to use restore_layout logic
    # Resolve Python Binary
    # Resolve Python Binary reliably
    if [[ -x "$NEXUS_HOME/.venv/bin/python3" ]]; then
        Python_BIN="$NEXUS_HOME/.venv/bin/python3"
    elif command -v python3 &>/dev/null; then
        Python_BIN="python3"
    else
        Python_BIN="python"
    fi
    export Python_BIN

IS_MOMENTUM=$("$Python_BIN" -c "
import json, os
try:
    with open('$COMP_JSON') as f:
        data = json.load(f)
        print('true' if data.get('momentum', False) else 'false')
except: print('false')
")
    
    if [[ "$IS_MOMENTUM" == "true" ]]; then
        echo "    [*] Composition identifies as Momentum Snapshot. Handing off to restore_layout..."
        export STATE_JSON=$("$Python_BIN" -c "import json; print(json.dumps(json.load(open('$COMP_JSON'))['layout']))")
        "$SCRIPT_DIR/restore_layout.sh" "$WINDOW_ID" "" "$PROJECT_ROOT"
        exit $?
    fi

    # Standard Composition processing
    START_PANE=$(tmux display-message -t "$WINDOW_ID" -p '#{pane_id}')
    
    echo "    [*] Processor target: $START_PANE, Root: $PROJECT_ROOT"
    
    # Explicitly export all required components for the processor
    export NEXUS_HOME="$NEXUS_HOME"
    export NEXUS_CORE="$NEXUS_CORE"
    export WRAPPER="$WRAPPER"
    export PROJECT_ROOT="$PROJECT_ROOT"
    export VIRTUAL_ROOT="${VIRTUAL_ROOT:-$PROJECT_ROOT}"
    
    # Resolve tool commands if not set
    export PARALLAX_CMD="${PARALLAX_CMD:-true}"
    export EDITOR_CMD="${EDITOR_CMD:-nvim}"
    export NEXUS_FILES="${NEXUS_FILES:-yazi}"
    export NEXUS_CHAT="${NEXUS_CHAT:-zsh}"

    # Execute the Python Processor
    LAYOUT_LOG="/tmp/nexus_layout.log"
    echo "[$(date +%T)] Starting Processor: $COMP_JSON" > "$LAYOUT_LOG"
    "$Python_BIN" "$SCRIPT_DIR/processor.py" "$COMP_JSON" "$START_PANE" "$PROJECT_ROOT" >> "$LAYOUT_LOG" 2>&1
    
    # Final Focus and State Save
    # --- Slot Invariant Anchoring ---
    i=1
    for p in $(tmux list-panes -t "$WINDOW_ID" -F '#{pane_id}'); do
        tmux set-option -p -t "$p" @nexus_slot "$i"
        ((i++))
    done

    tmux set-window-option -t "$WINDOW_ID" @nexus_last_composition "$LAYOUT"
    tmux select-pane -t "$START_PANE"
    exit 0
fi

# 2. Legacy Fallback (If no JSON found)
case "$LAYOUT" in
    vscodelike) build_vscodelike "$WINDOW_ID" "$PROJECT_ROOT" ;;
    *) echo "    [!] ERROR: Unknown composition '$LAYOUT'" >&2; exit 1 ;;
esac
