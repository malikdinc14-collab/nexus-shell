# Tasks: Nexus-Shell Composable Architecture

## Phase 1: Foundation & Requirements
- [x] Draft `requirements.md`
- [x] Draft `design.md`
- [x] Review with User

## Phase 2: Station & State Management
- [x] Implement `station_manager.sh`
  - [x] Create `/tmp` state directory structure
  - [x] Implement `nexus_station_init`
  - [x] Implement environment variable synchronization
- [ ] Write property test for Session Interoperability

## Phase 3: Composition System
- [x] Create `compositions/` registry
  - [x] Implement JSON parser for layouts (Python processor)
  - [x] Create default `vscodelike.json`
  - [x] Create `terminal.json`, `simple.json` compositions
- [x] Refactor `layout_engine.sh` to be data-driven
- [ ] Write property test for Deterministic Layout

## Phase 4: Multi-Window Interop
- [x] Update `launcher.sh` for named window support
  - [x] Implement `--composition` flag
  - [x] Implement project-wide session detection
  - [x] Add recursive boot guards (max 10 sessions)
- [ ] Implement command dispatch across windows

## Phase 5: Tabbed Modules
- [ ] Implement Shell-Tabs using tmux sub-windows
- [ ] Refactor Parallax into tabbed views

## Phase 6: Mouse-Free UI/UX
- [/] Consolidate keybindings in `load_keybinds.sh`
- [ ] Verify 100% keyboard coverage for all modules

## Phase 7: Integrated Agentic Workflow
- [ ] Implement `modules/spec_manager/`
- [ ] Create TUI for task management and status updates
- [ ] Implement PDD template generator
- [ ] Add automated walkthrough generation

## Phase 8: Station Kernel & Event Bus
- [x] Implement atomic State Store (`core/api/station_manager.sh`)
- [ ] Implement Unix-Socket Event Bus (`core/event_bus.sh`)
- [x] Create `nxs-state` CLI utility (in `shell_hooks.zsh`)

## Phase 9: Composition & Multi-Window Sync
- [ ] Implement "Follower Mode" for compositions
- [x] Refactor `launcher.sh` to leverage the new Kernel

## Phase 10: Repo Restructuring
- [x] Migrate scripts to `/core` and `/lib`
- [x] Enforce module standardization (manifests added)
- [x] Update tmux config paths for Nexus 2.0
- [x] Fix shell hooks paths

## Phase 11: Tool Integration (NEW)
- [x] Fix Parallax `--nexus` mode integration
- [ ] Implement AI Chat auto-launch (opencode/aider/gptme)
- [ ] Cross-pane file dispatch (Yazi → Nvim)
- [ ] Module marketplace / easy install

## Phase 12: Stability & Polish
- [x] Add environment propagation in layout_engine
- [x] Fix pane_wrapper crash handling
- [ ] Improve error messages and logging
- [ ] User acceptance testing
