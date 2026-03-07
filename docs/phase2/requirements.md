# Requirements: Nexus-Shell Phase 2 — Engine Layer

## 1. Intent & Scope
**Intent**: Transform the shell IDE from a "collection of tools in panes" into an integrated development engine where tools communicate, share state, and provide unified workflows for editing, debugging, building, and searching.
**Scope**: Phase 2 covers the engine subsystems that sit between the UI layer (Phase 1) and the user's code: IPC, search, build/task runners, session persistence, debugging, and AI integration.
**Depends on**: Phase 1 fully operational (stable sessions, pane lifecycle, working keybinds, menu system).

## 2. Core Principles
1. **Nvim is the Hub**: Neovim is not just an editor — it's the primary engine for code intelligence (via LSP), navigation (via Telescope), and debugging (via DAP). Nexus orchestrates around it.
2. **IPC via Existing Protocols**: Use tmux `send-keys`, nvim RPC (`--server`), and file-based state (`/tmp/nexus_*`). No custom daemons or event buses.
3. **Progressive Enhancement**: Each engine subsystem is independently useful. The user can adopt search without debugging, or persistence without AI integration.
4. **Tools Stay Swappable**: The engine layer provides integration *patterns*, not hardcoded wiring.

## 3. Functional Requirements

### 3.1 Project-Wide Search (Req-1)
- **3.1.1**: The user MUST be able to fuzzy-find files across the entire project from any pane
- **3.1.2**: The user MUST be able to grep across the codebase with live preview
- **3.1.3**: Search results MUST open in the editor pane (not a new terminal)
- **3.1.4**: Search MUST be powered by `ripgrep` + `fzf` (or Telescope inside nvim)
- **3.1.5**: A tmux keybind MUST trigger project-wide search from any pane context

### 3.2 Build & Task Runners (Req-2)
- **3.2.1**: The system MUST support defining project tasks in `.nexus.yaml` (e.g., `build`, `test`, `lint`)
- **3.2.2**: Tasks MUST be executable from the menu (ACTION items) or from the command prompt (`:build`, `:test`)
- **3.2.3**: Task output MUST appear in the terminal pane
- **3.2.4**: Build errors SHOULD be parseable and sent to Neovim's quickfix list via RPC
- **3.2.5**: A task runner module (`just`, `make`, or built-in) MUST be configurable per project

### 3.3 Session Persistence (Req-3)
- **3.3.1**: The tmux session layout (pane positions, sizes, and running commands) MUST be saveable
- **3.3.2**: Saved sessions MUST be restorable on next `nxs` launch
- **3.3.3**: Neovim buffer state (open files, cursor positions, folds) MUST be restorable
- **3.3.4**: The system MUST use `tmux-resurrect` / `tmux-continuum` for tmux state
- **3.3.5**: The system MUST use a Neovim session plugin (e.g., `mini.sessions`, `persistence.nvim`) for editor state

### 3.4 Debugging (DAP Integration) (Req-4)
- **3.4.1**: Neovim MUST be configured with `nvim-dap` for debug adapter protocol support
- **3.4.2**: Breakpoints, step-through, and variable inspection MUST be available inside the editor pane
- **3.4.3**: Debug configurations MUST be per-project (stored in `.nexus.yaml` or `launch.json`)
- **3.4.4**: A tmux keybind or menu item MUST launch the debugger for the current project
- **3.4.5**: Debug output/console MUST route to the terminal pane or a popup

### 3.5 AI Agent Integration (Req-5)
- **3.5.1**: The AI chat pane MUST be able to read context from the editor pane (current file, selection)
- **3.5.2**: The AI chat pane MUST be able to send commands to the terminal pane (run tests, execute scripts)
- **3.5.3**: Compiler/build errors SHOULD be pipeable to the AI agent for analysis
- **3.5.4**: The system MUST support multiple AI backends (opencode, gptme, aider) swappable via config
- **3.5.5**: AI integration MUST NOT require a custom IPC daemon — use tmux `send-keys` and nvim RPC

### 3.6 Version Control Integration (Req-6)
- **3.6.1**: Lazygit (or equivalent) MUST be accessible from the menu or a keybind
- **3.6.2**: In-editor git indicators (modified lines, blame) MUST be provided by a Neovim plugin (e.g., `gitsigns.nvim`)
- **3.6.3**: The tree pane (Yazi) SHOULD show git status indicators per file
- **3.6.4**: The system MUST support swapping the git UI tool via configuration

### 3.7 Global Theming (Req-7)
- **3.7.1**: A single theme configuration MUST control colors across tmux, nvim, yazi, and the menu
- **3.7.2**: Theme switching MUST be available via the command prompt (`:theme`) and the menu
- **3.7.3**: At minimum 3 built-in themes MUST be provided (dark, light, cyber)
- **3.7.4**: Active/inactive pane dimming MUST be configurable

## 4. Non-Functional Requirements

### 4.1 Performance (Req-8)
- **4.1.1**: Project-wide file search MUST return results in under 500ms for projects up to 100k files
- **4.1.2**: Build task dispatch MUST complete in under 200ms
- **4.1.3**: Session save/restore MUST complete in under 5 seconds

### 4.2 Compatibility (Req-9)
- **4.2.1**: MUST work with Neovim 0.10+
- **4.2.2**: MUST work with tmux 3.3+
- **4.2.3**: DAP adapters MUST be installable via Mason (Neovim package manager)
- **4.2.4**: MUST NOT require Docker, containers, or external services

## 5. Constraints
- **No custom daemons**: All IPC through tmux and nvim RPC. No background servers.
- **Nvim config is user-owned**: Nexus provides a reference config, not a mandatory one. Users can bring their own nvim setup.
- **No language-specific assumptions**: The engine must work for Python, JS, Rust, Go, etc. Language-specific features come from the LSP/DAP layer.
- **Phase 1 is prerequisite**: Do not start Phase 2 until sessions, panes, and keybinds are rock solid.
