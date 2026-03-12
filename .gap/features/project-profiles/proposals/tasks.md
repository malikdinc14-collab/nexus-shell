# Tasks: Project Profiles

## [ ] Phase 1: Environment Logic
- [ ] Create `config/profiles/` directory.
- [ ] Implement `core/env/profile_loader.sh` with `yq` parsing.
- [ ] Define the `base` and `focus` profiles.

## [ ] Phase 2: Shell Integration
- [ ] Create `core/exec/profile_switcher.sh`.
- [ ] Implement the `:profile` registry command.
- [ ] Add signal handling for hot-swapping themes across panes.

## [ ] Phase 3: Daemon Control
- [ ] Update Daemon Manager to start/kill services based on profile `daemons` list.
- [ ] Add profile state to `.nexus/state.json`.

## [ ] Phase 4: Verification
- [ ] Swap from `focus` to `swarm` and verify theme/composition/daemon updates.
