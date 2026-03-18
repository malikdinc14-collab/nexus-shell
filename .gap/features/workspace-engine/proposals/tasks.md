# Tasks: Multi-Folder Workspace Engine

## [ ] Phase 1: Core Logic
- [ ] Create `core/engine/workspace/workspace_manager.sh`.
- [ ] Implement `nxs_workspace_load` function with `jq` parsing.
- [ ] Export `NEXUS_ROOTS` and `NEXUS_WORKSPACE_NAME` to the global env.

## [ ] Phase 2: Search Core Update
- [ ] Modify `core/engine/search/live_grep.sh` to use multi-path ripgrep.
- [ ] Modify `core/engine/search/quick_find.sh` to use multi-path fd.

## [ ] Phase 3: UI & Commands
- [ ] Add `:workspace` command to the registry.
- [ ] Create TUI picker for recently used workspaces.
- [ ] Update the Status HUD (Phase 4.3) to display the active workspace.

## [ ] Phase 4: Verification
- [ ] Test aggregate search across 3 different physical directories.
- [ ] Verify environment persistence when switching Tmux windows.
