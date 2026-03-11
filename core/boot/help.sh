#!/bin/bash
# core/boot/help.sh — Nexus Help Screen
# Shows all keybinds, commands, and system info in a beautiful popup.

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"

cat << 'HEADER'
╔══════════════════════════════════════════════════════════════╗
║                     ⚡ NEXUS-SHELL ⚡                        ║
║              The Terminal IDE That Just Works                ║
╠══════════════════════════════════════════════════════════════╣
HEADER

cat << 'KEYBINDS'
║  KEYBINDS                                                    ║
║──────────────────────────────────────────────────────────────║
║  Navigation                                                  ║
║    Alt-1..5       Focus pane (tree/menu/editor/term/chat)    ║
║    Alt-h/j/k/l   Directional pane navigation                ║
║    Alt-[  Alt-]   Previous / next terminal tab               ║
║    Alt-=          New terminal tab                            ║
║                                                              ║
║  Tools                                                       ║
║    Alt-x          Escape current tool → menu                 ║
║    Alt-f          Find files (popup)                          ║
║    Alt-F          Live grep (popup)                           ║
║    Alt-g          Lazygit (popup)                             ║
║    Alt-i          Send editor context to AI                   ║
║    Alt-I          Send terminal errors to AI                  ║
║                                                              ║
║  Modes                                                       ║
║    Ctrl-\         Command prompt (:q, :help, :theme, etc.)   ║
║    Alt-Escape     Enter NORMAL mode (vim-like pane mgmt)     ║
║    Ctrl-Space     Toggle editor/render swap                   ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
KEYBINDS

cat << 'COMMANDS'
║  COMMANDS (via Ctrl-\)                                       ║
║──────────────────────────────────────────────────────────────║
║  Session                                                     ║
║    :q             Quit Nexus (kills all processes)            ║
║    :wq            Save all buffers and quit                   ║
║    :q!            Force quit (no save check)                  ║
║                                                              ║
║  Search                                                      ║
║    :find          Find files in project                       ║
║    :grep <text>   Live grep across project                    ║
║                                                              ║
║  Tasks                                                       ║
║    :build         Run build task from .nexus.yaml             ║
║    :test          Run test task                               ║
║    :lint          Run lint task                               ║
║                                                              ║
║  Tools                                                       ║
║    :git           Open lazygit                                ║
║    :ai            Send editor context to AI chat              ║
║    :ai-error      Send terminal errors to AI chat             ║
║                                                              ║
║  System                                                      ║
║    :theme         Switch theme (cyber/dark/light)             ║
║    :settings      Open settings menu                         ║
║    :help          Show this help                              ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
COMMANDS

cat << 'MENU'
║  MENU (in the menu pane)                                     ║
║──────────────────────────────────────────────────────────────║
║    Tools          Installed TUI tools (auto-discovered)       ║
║    Compositions   Switch layout (vscodelike, etc.)            ║
║    Settings       Edit config files                           ║
║    Find/Grep      Project search                              ║
║    Git            Lazygit                                     ║
║    Themes         Switch theme                                ║
║    Workspaces     Registered project directories               ║
║    Lists          Custom YAML menu definitions                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
MENU

echo ""
echo "  Press Enter to close"
read -r
