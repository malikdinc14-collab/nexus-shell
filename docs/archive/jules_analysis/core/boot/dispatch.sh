#!/bin/bash

# --- Nexus Global Command Dispatcher ---
# Handles commands from the ':' prompt in TMUX
# UI command dispatcher (TMUX)

CMD="$1"
NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
NEXUS_BIN="$NEXUS_HOME/bin"
NEXUS_CORE="$NEXUS_HOME/core"
NEXUS_BOOT="$NEXUS_KERNEL/boot"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"

# Load tools configuration
TOOLS_CONF="$NEXUS_HOME/tools.conf"
[[ -f "$TOOLS_CONF" ]] && source "$TOOLS_CONF"

# Binaries location
NEXUS_BIN_DIR="${NEXUS_BIN:-$HOME/.nexus-shell/bin}"
export PATH="$NEXUS_BIN_DIR:$PATH"

# Parallax Configuration Defaults
NEXUS_PX_UI="${NEXUS_PX_UI:-tmux}" # options: tmux, gum

# Determine project from session name
SESSION_NAME=$(tmux display-message -p '#S')
PROJECT_NAME=${SESSION_NAME#nexus_}
NVIM_PIPE="${NEXUS_PIPE:-$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe}"

case "$CMD" in
    # === Exit Commands ===
    "q"|":q")
        # Safe quit - check for unsaved changes
        if [[ -S "$NVIM_PIPE" ]]; then
            DIRTY=$("$NEXUS_BIN/nvim" --server "$NVIM_PIPE" --remote-expr "v:lua.is_dirty()" 2>/dev/null)
            if [[ "$DIRTY" == "true" ]]; then
                tmux display-message "Unsaved changes! Use :wq to save or :q! to force quit"
                exit 1
            fi
        fi
        "$NEXUS_BOOT/guard.sh" exit
        ;;
        
    "wq"|":wq")
        # Save and quit
        if [[ -S "$NVIM_PIPE" ]]; then
            tmux display-message "Saving buffers..."
            "$NEXUS_BIN/nvim" --server "$NVIM_PIPE" --remote-send ":wa<CR>" 2>/dev/null || tmux display-message "Failed to communicate with Neovim"
            sleep 0.5
        fi
        "$NEXUS_BOOT/guard.sh" exit
        ;;
        
    "q!"|":q!")
        # Force quit
        "$NEXUS_BOOT/guard.sh" force
        ;;
        
    # === View Commands ===
    "v"|":v")
        # Toggle Vision/Render mode
        "$NEXUS_HOME/lib/swap.sh"
        ;;

    "g"|":g")
        # Toggle Tree/Git mode
        "$NEXUS_HOME/lib/tree_swap.sh"
        ;;

    # === AI Control ===
    "kill"|":kill")
        # Terminate active agent loops
        "$NEXUS_HOME/scripts/kill_agent.sh"
        ;;
    
    "down"|":down")
        # Unload all local models and backends
        "$NEXUS_HOME/scripts/unload_brains.sh"
        ;;

    "spawn"|":spawn")
        # Open a new terminal tab for a specific view
        # Usage: :spawn 2 (for Monitor)
        TARGET="${2:-0}"
        "$NEXUS_BIN/px-window-spawn" "$TARGET"
        ;;

    # === Pane Navigation ===
    "n"|":n")
        tmux select-pane -t "${PX_NEXUS_TREE_PANE}" 2>/dev/null || tmux select-pane -t tree 2>/dev/null || tmux select-pane -t 0
        ;;
    "p"|":p")
        tmux select-pane -t "${PX_NEXUS_PARALLAX_PANE}" 2>/dev/null || tmux select-pane -t parallax 2>/dev/null || tmux select-pane -t 1
        ;;
    "e"|":e")
        tmux select-pane -t "${PX_NEXUS_EDITOR_PANE}" 2>/dev/null || tmux select-pane -t editor 2>/dev/null || tmux select-pane -t 2
        ;;
    "t"|":t")
        tmux select-pane -t "${PX_NEXUS_TERMINAL_PANE}" 2>/dev/null || tmux select-pane -t terminal 2>/dev/null || tmux select-pane -t 3
        ;;
    "c"|":c")
        tmux select-pane -t "${PX_NEXUS_CHAT_PANE}" 2>/dev/null || tmux select-pane -t chat 2>/dev/null || tmux select-pane -t 4
        ;;

    # === Theme ===
    "theme"|":theme")
        "$NEXUS_SCRIPTS/theme.sh" menu
        ;;

    # === Parallax Commands ===
    "px"|"parallax"|":px"|":parallax")
        # Focus the resident Parallax pane
        tmux select-pane -t "${PX_NEXUS_PARALLAX_PANE}" 2>/dev/null || tmux select-pane -t parallax 2>/dev/null || tmux select-pane -t 1
        ;;

    "a"|"actions"|":a"|":actions")
        # Switch resident Parallax to library and focus
        tmux send-keys -t "${PX_NEXUS_PARALLAX_PANE:-parallax}" "library" Enter
        tmux select-pane -t "${PX_NEXUS_PARALLAX_PANE:-parallax}"
        ;;

    # === Help ===
    "help"|":help"|"?"|":?")
        tmux display-popup -E -w 60% -h 70% "cat << 'EOF'
╔══════════════════════════════════════════════════════════╗
║                  NEXUS-SHELL COMMANDS                    ║
╠══════════════════════════════════════════════════════════╣
║  EXIT                                                    ║
║    :q      - Quit (checks for unsaved changes)           ║
║    :wq     - Save all and quit                           ║
║    :q!     - Force quit                                  ║
║                                                          ║
║  NAVIGATION                                              ║
║    :n      - Focus Navigator (Tree)                      ║
║    :p      - Focus Parallax Dashboard                    ║
║    :e      - Focus Editor                                ║
║    :t      - Focus Terminal                              ║
║    :c      - Focus Chat                                  ║
║                                                          ║
║  PARALLAX                                                ║
║    :a      - Switch to Quick Actions                     ║
║                                                          ║
║  VIEW                                                    ║
║    :v      - Toggle Editor/Render mode                   ║
║    :theme  - Change color theme                          ║
║                                                          ║
║  RESIZE (After Alt-Esc)                                  ║
║    Shift+H/J/K/L - Resize panes                          ║
║                                                          ║
║  Press Enter to close                                    ║
╚══════════════════════════════════════════════════════════╝
EOF
read"
        ;;

    # === Fallback ===
    *)
        # 1. Check for Agent query (starts with ! or is unknown)
        if [[ "$CMD" == "!"* ]]; then
            # Query the agent directly
            QUERY="${CMD#!}"
            "$NEXUS_HOME/scripts/px-bridge-agent.sh" "$QUERY"
        elif [[ -n "$CMD" ]]; then
            # Try as a nexus command, if fails, send to agent as general query
            # (In testing phase, we treat any unknown :command as a query)
            "$NEXUS_HOME/scripts/px-bridge-agent.sh" "$CMD"
        fi
        ;;
esac
