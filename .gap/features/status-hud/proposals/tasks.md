# Tasks: Status HUD

## [ ] Phase 1: Telemetry Core
- [ ] Create `/tmp/nexus_telemetry.json` initialization logic.
- [ ] Implement `core/hud/telemetry_aggregator.sh`.

## [ ] Phase 2: Renderer implementation
- [ ] Create `core/hud/renderer.sh` (Bash/ANSI or Python).
- [ ] Design the layout strip (Pulse | Workspace | Locality).

## [ ] Phase 3: Tmux Provisioning
- [ ] Implement `core/hud/hud_window_manager.sh` to pin the status window.
- [ ] Update `nexus.conf` to handle HUD window visibility.

## [ ] Phase 4: Verification
- [ ] Simulate telemetry updates and verify HUD response time.
