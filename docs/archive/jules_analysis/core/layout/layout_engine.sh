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
    tmux split-window -h -b -l 30 -t "$CENTER_PANE" -c "$PROJECT_ROOT" "$WRAPPER $NEXUS_FILES '$PROJECT_ROOT'"
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
    nxs_assert "Editor Initiation"
    
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
export WRAPPER="$NEXUS_KERNEL/boot/pane_wrapper.sh"
export BRIDGE="$NEXUS_CORE/bridge"

WINDOW_ID="$1"
LAYOUT="$2"
SESSION_ID="$3"
PROJECT_ROOT="$4"

echo "    [*] Seeking Composition: $LAYOUT"

# 1. Check for JSON Composition in compositions/
COMP_JSON="$NEXUS_HOME/compositions/$LAYOUT.json"

if [[ -f "$COMP_JSON" ]]; then
    echo "    [*] Applying Data-Driven Composition..."
    # Get the starting pane ID for this window
    START_PANE=$(tmux display-message -t "$WINDOW_ID" -p '#{pane_id}')
    
    # Ensure all required environment variables are exported for the Python processor
    # These may have been set by launcher.sh but need to be explicitly exported
    export WRAPPER="${WRAPPER:-$NEXUS_KERNEL/boot/pane_wrapper.sh}"
    export PARALLAX_CMD="${PARALLAX_CMD:-echo 'Parallax not configured'}"
    export EDITOR_CMD="${EDITOR_CMD:-nvim}"
    export NEXUS_FILES="${NEXUS_FILES:-yazi}"
    export NEXUS_CHAT="${NEXUS_CHAT:-zsh}"
    
    echo "    [*] Processor target: $START_PANE, Root: $PROJECT_ROOT"
    
    # Execute the Python Processor
    python3 "$SCRIPT_DIR/processor.py" "$COMP_JSON" "$START_PANE" "$PROJECT_ROOT"
    
    # Final Focus
    tmux select-pane -t "$START_PANE"
    exit 0
fi

# 2. Legacy Fallback (If no JSON found)
case "$LAYOUT" in
    vscodelike) build_vscodelike "$WINDOW_ID" "$PROJECT_ROOT" ;;
    *) echo "    [!] ERROR: Unknown composition '$LAYOUT'" >&2; exit 1 ;;
esac
