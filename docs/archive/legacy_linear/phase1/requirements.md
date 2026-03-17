# Requirements: Nexus-Shell Phase 1 — UI & Session Layer

## 1. Intent & Scope
**Intent**: Build a cohesive, modular shell IDE that feels like a single application despite being composed of independent terminal programs (nvim, yazi, opencode, fzf, tmux).
**Scope**: Phase 1 covers the UI/UX layer — session lifecycle, pane management, menu system, configuration, and keybinds. The "engine" layer (LSP orchestration, DAP, build runners, session persistence) is explicitly deferred to Phase 2.

## 2. Core Principles
1. **Modularity**: Every tool is swappable. The user can replace nvim with micro, yazi with ranger, opencode with gptme. The system must not hardcode tool assumptions.
2. **Configuration-Driven**: Layouts, keybinds, tools, and menus are defined in YAML/JSON files, never hardcoded in scripts.
3. **One App Feel**: Keybinds, focus behavior, and visual theming must make the user forget they're in tmux. No visible seams between tools.
4. **Indestructible Panes**: A pane must never die or go blank. If a tool exits, the pane must remain useful (shell or menu).
5. **Clean Lifecycle**: Sessions must start cleanly, exit cleanly (`:q`), and never leave zombies.

## 3. Functional Requirements

### 3.1 Session Lifecycle (Req-1)
- **3.1.1**: `nxs` MUST create a single tmux session per project, named `nexus_<project>`
- **3.1.2**: `nxs` MUST detect and refuse recursive invocations
- **3.1.3**: `nxs` MUST propagate all environment variables (`NEXUS_HOME`, `NEXUS_PROJECT`, etc.) to the tmux session environment
- **3.1.4**: Environment variables MUST be accessible in `run-shell` contexts (set globally, not just per-session)
- **3.1.5**: `:q` (via `Ctrl-\`) MUST cleanly kill the tmux session and all child processes
- **3.1.6**: Detaching from a session MUST NOT leave zombie processes
- **3.1.7**: Re-attaching to an existing session MUST work without creating duplicates

### 3.2 Pane Lifecycle (Req-2)
- **3.2.1**: Each pane MUST run its designated tool wrapped by `pane_wrapper.sh`
- **3.2.2**: When a tool exits (any exit code), the pane MUST drop to an interactive shell (`/bin/zsh -i`), NOT restart the tool
- **3.2.3**: There MUST be a dedicated tmux keybind to kill the current pane's foreground process and launch the tools menu (`nexus-menu`) in its place
- **3.2.4**: The pane wrapper MUST cleanly exit when receiving SIGTERM/SIGHUP (session kill)
- **3.2.5**: The pane wrapper MUST NOT log visible output to the pane (logging goes to a file only)

### 3.3 Menu System (Req-3)
- **3.3.1**: The menu MUST be an infinite FZF loop that never exits (always returns to menu on Escape)
- **3.3.2**: The menu MUST support hierarchical navigation (home → tools, home → compositions, etc.)
- **3.3.3**: When a tool is launched from the menu (ACTION type), it MUST run in-pane, replacing the menu
- **3.3.4**: When a tool exits, the menu MUST resume at the **same context** the user was in (e.g., tools list, not home)
- **3.3.5**: The menu MUST be data-driven — contexts defined by YAML files and auto-discovery, not hardcoded

### 3.4 Composition System (Req-4)
- **3.4.1**: Layouts MUST be defined in JSON composition files
- **3.4.2**: The layout engine MUST support nested horizontal and vertical splits with percentage sizing
- **3.4.3**: Each pane in a composition MUST have a named `id` used as the tmux pane title
- **3.4.4**: Compositions MUST support variable expansion (`$EDITOR_CMD`, `$NEXUS_CHAT`, etc.)

### 3.5 Keybind System (Req-5)
- **3.5.1**: `Ctrl-\` MUST open a command prompt (`:` prefix) dispatching to the command registry
- **3.5.2**: `Alt-1` through `Alt-5` MUST focus panes by index
- **3.5.3**: `Alt-hjkl` MUST provide directional pane navigation
- **3.5.4**: `Alt-[` / `Alt-]` MUST cycle terminal tabs (within the terminal pane)
- **3.5.5**: A dedicated keybind (e.g., `Alt-x`) MUST escape the current tool and open the tools menu
- **3.5.6**: Keybinds MUST NOT conflict with tool-internal bindings (nvim, yazi, opencode all use their own keys)

### 3.6 Command Registry (Req-6)
- **3.6.1**: Commands MUST be defined in `core/engine/api/registry.json`
- **3.6.2**: The dispatch system MUST resolve commands by name and execute their action
- **3.6.3**: Preflight checks (e.g., `check_dirty`) MUST be non-fatal — failures default to "safe to proceed"
- **3.6.4**: Unknown commands MUST show a helpful message, not crash

### 3.7 Configuration (Req-7)
- **3.7.1**: Global settings MUST live in `config/` (tmux conf, yazi conf, tool defaults)
- **3.7.2**: Per-project overrides MUST be supported via `.nexus.yaml` in the project root
- **3.7.3**: Tool assignments (`NEXUS_EDITOR`, `NEXUS_CHAT`, `NEXUS_FILES`) MUST be configurable
- **3.7.4**: The menu MUST provide access to edit configurations (opening config files in the editor)

## 4. Non-Functional Requirements

### 4.1 Performance (Req-8)
- **4.1.1**: Session startup MUST complete in under 3 seconds
- **4.1.2**: Menu rendering (FZF) MUST be instant (< 100ms)
- **4.1.3**: Keybind dispatch MUST complete in under 500ms

### 4.2 Compatibility (Req-9)
- **4.2.1**: MUST work on macOS with iTerm2, Kitty, or Alacritty
- **4.2.2**: MUST work with tmux 3.3+
- **4.2.3**: MUST work with Python 3.10+ (for the menu engine)
- **4.2.4**: MUST NOT require root or sudo

## 5. Constraints
- **No auto-restart**: Tools must NOT be automatically restarted on exit. The user decides.
- **No IPC bus**: Phase 1 has no event bus. Tools communicate only via tmux `send-keys` and environment variables.
- **No state persistence**: Session restore (tmux-resurrect) is Phase 2.
- **No AI orchestration**: AI tools (opencode, gptme) are just pane commands. Smart routing is Phase 2.
