# Tasks: Nexus-Shell Phase 2 — Engine Layer Implementation

> **Prerequisite**: All Phase 1 tasks must be complete and verified before starting Phase 2.

## Phase 2.1: Project-Wide Search
- [ ] **2.1.1: Quick File Search popup** (Req-1.1, Req-1.5, Design 2.1.1)
  - [ ] Create `core/search/quick_find.sh` using `fd` + `fzf` in a `tmux display-popup`
  - [ ] Wire selected file to nvim editor pane via `--remote` RPC
  - [ ] Add `Alt-f` keybind in `nexus.conf` for quick file search
  - [ ] Auto-focus the editor pane after file selection

- [ ] **2.1.2: Deep Code Search** (Req-1.2, Req-1.3, Design 2.1.2)
  - [ ] Ship a reference Neovim config with Telescope + ripgrep pre-configured
  - [ ] Ensure `<Leader>ff` (find files) and `<Leader>fg` (live grep) work out of the box
  - [ ] Document how users can bring their own nvim search config

## Phase 2.2: Build & Task Runner
- [ ] **2.2.1: Task definition schema** (Req-2.1, Design 2.2)
  - [ ] Extend `.nexus.yaml` schema to support `tasks:` block
  - [ ] Define schema: `command`, `output` (terminal/popup), `on_error` (quickfix/ignore)
  - [ ] Update `config_helper.py` to parse task definitions

- [ ] **2.2.2: Task execution** (Req-2.2, Req-2.3, Design 2.2)
  - [ ] Create `core/exec/task_runner.sh` that runs tasks in the terminal pane
  - [ ] Add tasks as ACTION items in the menu engine (new "Tasks" context)
  - [ ] Register `:build`, `:test`, `:lint` commands dynamically from `.nexus.yaml`

- [ ] **2.2.3: Quickfix integration** (Req-2.4, Design 2.2)
  - [ ] Capture task stderr to a temp file
  - [ ] Parse error output and send to nvim quickfix list via RPC
  - [ ] Support format strings for different compilers (gcc, rustc, python tracebacks)

## Phase 2.3: Session Persistence
- [ ] **2.3.1: Tmux state persistence** (Req-3.1, Req-3.2, Design 2.3.1)
  - [ ] Add `tmux-resurrect` to the tmux plugin list in `nexus.conf`
  - [ ] Configure auto-save interval via `tmux-continuum`
  - [ ] Add `:save` and `:restore` commands to the command registry

- [ ] **2.3.2: Neovim session persistence** (Req-3.3, Design 2.3.2)
  - [ ] Add `persistence.nvim` or `mini.sessions` to the reference nvim config
  - [ ] Configure auto-save on `VimLeavePre` when `$NEXUS_STATION_ACTIVE` is set
  - [ ] Configure auto-restore on nvim startup inside a Nexus session

- [ ] **2.3.3: Unified save/restore** (Req-3.1, Design 2.3.3)
  - [ ] Create `core/session/persist.sh` that triggers both tmux and nvim saves
  - [ ] Modify `bin/nxs` to detect saved state and offer restore on launch

## Phase 2.4: Debugging (DAP)
- [ ] **2.4.1: Reference debug config** (Req-4.1, Req-4.2, Design 2.4)
  - [ ] Add `nvim-dap` and `nvim-dap-ui` to the reference nvim config
  - [ ] Pre-configure adapters for Python (debugpy), Rust (codelldb), and Node (js-debug-adapter)
  - [ ] Verify breakpoints, step-through, and variable inspection work

- [ ] **2.4.2: Project debug configs** (Req-4.3, Design 2.4)
  - [ ] Extend `.nexus.yaml` schema to support `debug:` block
  - [ ] Write a bridge that converts `.nexus.yaml` debug configs to nvim-dap format
  - [ ] Support per-language adapter specification

- [ ] **2.4.3: Debug keybinds and menu** (Req-4.4, Req-4.5, Design 2.4)
  - [ ] Add "Debug" context to the menu engine
  - [ ] Add `:debug` command to the registry (launches current file with DAP)
  - [ ] Route debug console output to the terminal pane or a popup

## Phase 2.5: AI Agent Integration
- [ ] **2.5.1: Context passing** (Req-5.1, Design 2.5.1)
  - [ ] Create `core/ai/send_context.sh` that reads current nvim buffer via RPC
  - [ ] Send buffer content to the AI pane via `tmux send-keys`
  - [ ] Add "Send to AI" action to the menu

- [ ] **2.5.2: Error piping** (Req-5.2, Req-5.3, Design 2.5.2)
  - [ ] Create `core/ai/pipe_error.sh` that captures terminal pane output
  - [ ] Send captured output to the AI pane for analysis
  - [ ] Add `:ai-error` command to the registry

- [ ] **2.5.3: Multi-backend support** (Req-5.4, Design 2.5)
  - [ ] Ensure `$NEXUS_CHAT` variable correctly switches between opencode, gptme, aider
  - [ ] Test context passing and error piping with each backend
  - [ ] Document backend-specific configuration

## Phase 2.6: Version Control
- [ ] **2.6.1: Lazygit integration** (Req-6.1, Design 2.6)
  - [ ] Add lazygit as a tool in the menu engine (auto-discovered from `modules/lazygit/`)
  - [ ] Verify in-pane launch and exit behavior
  - [ ] Consider `Alt-g` as a direct keybind to toggle lazygit in a popup

- [ ] **2.6.2: In-editor git indicators** (Req-6.2, Design 2.6)
  - [ ] Add `gitsigns.nvim` to the reference nvim config
  - [ ] Configure gutter signs, inline blame, and hunk staging
  - [ ] Add keybinds for hunk navigation (`]c`, `[c`)

- [ ] **2.6.3: File tree git status** (Req-6.3, Design 2.6)
  - [ ] Configure Yazi to show git status indicators (if supported)

## Phase 2.7: Global Theming
- [ ] **2.7.1: Theme file format** (Req-7.1, Design 2.7)
  - [ ] Create `config/themes/` directory with 3 built-in themes (cyber, dark, light)
  - [ ] Define YAML schema for theme files (tmux, nvim, yazi sections)

- [ ] **2.7.2: Theme application engine** (Req-7.2, Design 2.7)
  - [ ] Update `core/boot/theme.sh` to read YAML theme files
  - [ ] Apply tmux colors via `set-option`
  - [ ] Apply nvim colorscheme via RPC
  - [ ] Apply Yazi theme via config file write

- [ ] **2.7.3: Active/inactive pane dimming** (Req-7.4, Design 2.7)
  - [ ] Add `window-style` and `window-active-style` to `nexus.conf`
  - [ ] Make dim amount configurable per theme

## Phase 2.8: Integration Testing
- [ ] **2.8.1: Search workflow** (AC-1)
  - [ ] `Alt-f` → popup file finder → select file → opens in editor pane
  - [ ] Inside nvim: `<Leader>fg` → live grep → select result → jumps to line

- [ ] **2.8.2: Build workflow** (AC-2)
  - [ ] Define `test` task in `.nexus.yaml` → `:test` runs it in terminal pane
  - [ ] Build failure → errors appear in nvim quickfix list

- [ ] **2.8.3: Debug workflow** (AC-3)
  - [ ] Set breakpoint in nvim → `:debug` → program stops at breakpoint
  - [ ] Step through code, inspect variables in DAP UI

- [ ] **2.8.4: Session workflow** (AC-4)
  - [ ] Open multiple files, arrange panes → `:save` → `:q`
  - [ ] Re-run `nxs` → layout and files restored

## Success Criteria
- File search finds and opens files in under 500ms from any pane
- Build errors from the terminal appear in nvim's quickfix list
- Session layout and editor state survive a full quit/restart cycle
- DAP breakpoints work for at least 2 languages
- AI context passing works with at least 2 backends
- Theme switch updates all tools simultaneously
