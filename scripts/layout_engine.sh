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
    tmux split-window -v -p 25 -t "$CHAT_PANE" -c "$PROJECT_ROOT" "$WRAPPER $SCRIPT_DIR/transaction_ui.sh"
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
SCRIPT_DIR="$(cd -P "$(dirname "$0")" && pwd)"
WRAPPER="$SCRIPT_DIR/pane_wrapper.sh"

WINDOW_ID="$1"
LAYOUT="$2"
SESSION_ID="$3"
PROJECT_ROOT="$4"

case "$LAYOUT" in
    vscodelike) build_vscodelike "$WINDOW_ID" "$PROJECT_ROOT" ;;
    monitor)
        tmux send-keys -t "$WINDOW_ID.0" "$WRAPPER top" Enter
        tmux split-window -v -b -p 20 -t "$WINDOW_ID.0" -c "$PROJECT_ROOT" "$WRAPPER $PARALLAX_CMD --context workflow:tasks"
        tmux split-window -h -p 50 -t "$WINDOW_ID.1" -c "$PROJECT_ROOT" "$WRAPPER tail -f /tmp/px-agent-trace.log"
        ;;
esac
