# Tasks: Nexus Shell Integration & Spec Manager

## Phase 1: Core System Hardening
- [ ] **Fix Phase 4 Audit Bugs**: Resolve hot-swap traps in `nxs-view`, fix secret leaks in `nxs-keys`, and repair `menu_engine` profile detection.
- [ ] **Universal Hot-Swap Registry**: Implement the global `Alt-r` (Render) / `Ctrl-e` (Edit) dispatcher in Tmux and `user.conf`.

## Phase 2: Spec Manager Implementation (GAP Harness)
- [ ] **Gate Engine State Machine**: Implement `core/kernel/exec/nxs-gate.sh` to track mission state in `.gap/state.json`.
- [ ] **Requirement-Prop-Task Linker**: Create the automated traceability parser as a `menu_engine` extension.
- [ ] **Artifact Multi-Tab Dispatcher**: Update `nxs-gap-spec.sh` to support high-fidelity rendering for all 4 gates across split panes.

## Phase 3: Governance & Security
- [ ] **Plan-to-ACL Enforcer**: Build the plan parser that informs `nxs-agent-boot.sh` of permitted tool paths.
- [ ] **Event Bus Integration**: Wire all integration scripts to publish telemetry to the Nexus Event Bus.

## Phase 4: Final Verification
- [ ] **School Integration Test**: Verify that the School profile correctly boots a GAP mission with restricted ACLs and live Vision previews.
