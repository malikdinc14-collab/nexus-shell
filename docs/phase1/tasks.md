# Tasks: Nexus-Shell Phase 1 — UI & Session Layer

## Phase 1.1: Critical Fixes (Unblocks Everything)
- [ ] **1.1.1: Fix `:q` quit command** (Req-1.5, Design 2.1, 2.5)
  - [ ] Change `bin/nxs` to use `tmux set-environment -g` for `NEXUS_HOME`, `NEXUS_CORE`, `NEXUS_BOOT`
  - [ ] Verify `$NEXUS_HOME` resolves inside `run-shell` context
  - [ ] Test `Ctrl-\ → q → Enter` cleanly kills the session

- [ ] **1.1.2: Rewrite `pane_wrapper.sh`** (Req-2.2, Req-2.4, Design 2.2)
  - [ ] Remove the infinite restart loop entirely
  - [ ] Run the command once, then `exec /bin/zsh -i` on exit
  - [ ] Remove all stdout logging (keep file logging only)
  - [ ] Verify SIGTERM/SIGHUP causes clean exit (no shell fallback)

- [ ] **1.1.3: Kill zombie sessions** (Req-1.6)
  - [ ] Run `tmux kill-server` to clear existing zombies
  - [ ] Test that re-launching `./bin/nxs` creates exactly one session

## Phase 1.2: Pane Escape & Menu Improvements
- [ ] **1.2.1: Add escape-to-menu keybind** (Req-2.3, Req-5.5, Design 2.3)
  - [ ] Add `Alt-x` keybind in `nexus.conf` using `tmux respawn-pane -k`
  - [ ] Verify it works from nvim, yazi, opencode, and plain shell
  - [ ] Verify it launches `nexus-menu` in the respawned pane

- [ ] **1.2.2: Fix nvim pipe conflict** (Req-1.6, Design 2.2)
  - [ ] Ensure `bin/nxs` cleans up stale nvim pipes on startup
  - [ ] Verify nvim launches cleanly in a fresh session

- [ ] **1.2.3: Menu context persistence** (Req-3.4, Design 2.4)
  - [ ] Verify `CURRENT_CTX` persists across tool launches in `nexus-menu`
  - [ ] Test: navigate to tools → launch nvim → quit nvim → should return to tools list

## Phase 1.3: Keybind Audit & Cleanup
- [ ] **1.3.1: Remove conflicting keybinds** (Req-5.6)
  - [ ] Audit all `Alt-*` binds in `nexus.conf` for conflicts
  - [ ] Remove duplicate `M-p` binding (line 40 and line 105)
  - [ ] Remove dead references to `PX_NEXUS_PARALLAX_PANE`
  - [ ] Rename all "parallax" references to "menu" in `nexus.conf` and `registry.json`

- [ ] **1.3.2: Clean up stale keybind targets** (Req-5.1, Req-6.4)
  - [ ] Remove `px-audit` reference from `M-a` binding
  - [ ] Remove `px-bridge-agent` fallback from `dispatch.sh`
  - [ ] Verify all keybinds point to scripts that exist

## Phase 1.4: Configuration & Layout Polish
- [ ] **1.4.1: Validate composition system** (Req-4, Design 2.6)
  - [ ] Test `vscodelike.json` produces correct 5-pane layout
  - [ ] Verify all pane titles are set correctly (files, menu, editor, terminal, chat)
  - [ ] Test that `$NEXUS_CHAT`, `$NEXUS_EDITOR`, `$NEXUS_FILES` are correctly expanded

- [ ] **1.4.2: Configuration menu items** (Req-7.4, Req-3.5)
  - [ ] Add "Settings" item to home menu that opens config files in the editor pane
  - [ ] Add "Compositions" menu item that lists available layouts

## Phase 1.5: Integration Testing
- [ ] **1.5.1: Full lifecycle test** (AC-1)
  - [ ] `./bin/nxs` → 5-pane layout with correct tools in each pane
  - [ ] `Ctrl-\ → q` → session cleanly exits, no zombies
  - [ ] Re-run `./bin/nxs` → creates fresh session without "session limit" error

- [ ] **1.5.2: Pane lifecycle test** (AC-2)
  - [ ] Exit opencode → pane drops to shell
  - [ ] `Alt-x` → current tool killed, menu appears
  - [ ] Select tool from menu → runs in-pane
  - [ ] Quit tool → menu resumes at same context

- [ ] **1.5.3: Keybind test** (AC-3)
  - [ ] `Alt-1..5` → focuses correct pane
  - [ ] `Ctrl-\ → help` → shows command list
  - [ ] `Alt-[` / `Alt-]` → cycles terminal tabs

## Success Criteria
- Session starts in under 3 seconds with correct layout
- `:q` cleanly kills session on first attempt
- No zombie tmux sessions after normal or abnormal exit
- All 5 panes recover gracefully when their tool exits
- `Alt-x` reliably escapes any tool to the menu
- Menu context persists across tool launches
