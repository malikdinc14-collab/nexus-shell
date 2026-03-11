# Plan: Agent Zero Headless Migration

## Authority & Governance
Authorized execution parameters for the headless migration.

### 1. Model Selection
- **Orchestrator**: Antigravity (Me)
- **Worker**: Authorized for `gemini-2.5-flash` via `@google/gemini-cli`.

### 2. Inference Locality
- All code transformations MUST occur locally on the host machine.
- No external model APIs beyond the authorized local CLI are permitted to read the Agent Zero core logic.

### 3. Execution Dependency
- This plan is LOCKED until human approval is moved to the `.gap/` ledger.
