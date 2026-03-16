# Design: Nexus Shell Integrations Architecture

## 1. Modular Integration Layer
- **nxs-view Dispatcher**: All visual pods enter through a centralized renderer. It detects terminal capabilities (Kitty Graphics) and selects the best visualization engine (Glow, Mmdc, Bat).
- **nxs-agent Orchestrator**: Uses a `default.yaml` manifest to decouple the agent front-end from its environment. Injecting context and Keychain keys at spawn-time.
- **Event Mesh**: All integration bash scripts publish to a Unix domain socket server, allowing independent panes to synchronize (e.g., advancing a gate in Pane 1 refreshes the Vision view in Pane 2).

## 2. Spec Manager Components
- **Gate Engine**: A JSON state machine tracking the mission lifecycle. It blocks/unblocks file access based on the current active gate.
- **Traceability Linker**: A regex-based parser that maps implementation tasks back to requirements via property-based invariants.
- **ACL Kernel**: A logic layer that parses approved plans and interfaces with `nxs-agent-boot.sh` to restrict tool-access (Write/Exec).

## 3. The 3-Layer Cascading Discovery
Integrations discover scripts and profiles through a cascading lookup:
1.  **Global** (`$NEXUS_HOME/global/`)
2.  **Profile** (`$NEXUS_HOME/config/profiles/`)
3.  **Project** (`$PROJECT_ROOT/.nexus/`) — Highest authority.
