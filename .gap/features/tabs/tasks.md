# Tasks: Universal Tab Stacks

This document outlines the implementation roadmap for the Universal Tab Stacks architecture.

## Phase 1: Identity Decoupling
### [MODIFY] [layout_engine.sh](file:///Users/Shared/Projects/nexus-shell/core/kernel/layout/layout_engine.sh)
- Remove all default `@nexus_role` and `@nexus_slot` assignments.
- Ensure initial panes start as anonymous shell containers.

### [MODIFY] [stack](file:///Users/Shared/Projects/nexus-shell/core/kernel/stack/stack)
- Remove the `@nexus_slot` fallback from `resolve_role`.
- Ensure `Alt-N` initiates a fresh UUID stack for any anonymous pane.

## Phase 2: Interface & Adapters
### [MODIFY] [daemon.py](file:///Users/Shared/Projects/nexus-shell/core/services/internal/daemon.py)
- Define `BaseContainerAdapter` (ABC).
- Implement `TmuxAdapter` to wrap existing tmux logic.
- Implement **`WindowAdapter`** (Stub/Initial) to handle standalone terminal identification.
- Refactor `Daemon.handle_stack_op` to use the adapter interface.

### [NEW] [ipc_bridge.sh](file:///Users/Shared/Projects/nexus-shell/core/kernel/boot/ipc_bridge.sh)
- Implement a lightweight focus-reporting script for standalone windows (using OSC 7/OSC 52 or similar).

## Phase 3: Global Registry & Logical Reservoir
### [MODIFY] [daemon.py](file:///Users/Shared/Projects/nexus-shell/core/services/internal/daemon.py)
- Transition state model to a UUID-based Stack Registry.
- Implement **Logical Backgrounding**: Replace the hardcoded `RESERVOIR` window logic with a `status: BACKGROUND` attribute in the registry.

### [NEW] [nxs-stack](file:///Users/Shared/Projects/nexus-shell/bin/nxs-stack)
- Implement the CLI interface for `push`, `switch`, `close`, and `identity`.
- Ensure it communicates via the Daemon's IPC socket.

## Phase 4: Coordinate-Aware Restoration
### [MODIFY] [save_layout.py](file:///Users/Shared/Projects/nexus-shell/core/kernel/layout/save_layout.py)
- Record proportional coordinates (x, y, w, h) for each stack.
### [NEW] [restoration_orchestrator.py](file:///Users/Shared/Projects/nexus-shell/core/engine/orchestration/restoration_orchestrator.py)
- Implement geometric mapping logic to reconnect stacks to physical containers after reboot.

## Phase 5: Verification & Cleanup
- Verify focus sovereignty across splits.
- Verify cross-window orchestration (independent terminal windows).
- Final code cleanup and documentation update.
