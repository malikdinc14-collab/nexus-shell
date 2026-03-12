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
║    Alt-1..9       Jump to Window Slot 1-9                    ║
║    Alt-0          Jump to Window Slot 10                     ║
║    Alt-[  Alt-]   Prev / Next Tab (role-specific)           ║
║    Alt-=          New Tab in focused pane                   ║
║    Alt-w          Close current Tab                         ║
║    Alt-h/j/k/l    Focus pane (left/down/up/right)           ║
║    Shift-H / L    Previous / Next Editor Tab (Buffer)        ║
║    [b / ]b        Previous / Next Editor Tab (Buffer)        ║
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
║  Sovereignty                                                 ║
║    :gap           Launch autonomous GAP mission              ║
║    :keychain      Manage secure API keys                     ║
║    :guard         Edit safety registry                        ║
║                                                              ║
║  Session                                                     ║
║    :q             Quit Nexus (kills all processes)            ║
║    :wq            Save all buffers and quit                   ║
║    :wqa           Save all windows and quit                   ║
║    :q!            Force quit (no save check)                  ║
║                                                              ║
║  Search                                                      ║
║    :find          Find files in project                       ║
║    :grep <text>   Live grep across project                    ║
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
║    Sovereignty    Autonomous missions, Guard, & Keychain      ║
║    Tools          Installed TUI tools (auto-discovered)       ║
║    Compositions   Switch layout (vscodelike, etc.)            ║
║    Settings       Edit config files                           ║
║    Workspaces     Registered project directories               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
MENU

echo ""
echo "  Press Enter to close"
read -r
