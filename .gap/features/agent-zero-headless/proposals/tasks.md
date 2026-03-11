# Tasks: Agent Zero Headless Migration

## Phase 1: Core Decoupling
- [ ] **1.1: Entry Point Analysis**
    - [ ] Identify Gradio-free initialization logic in Agent Zero's `main.py`.
- [ ] **1.2: Headless Entry Point**
    - [ ] Create `modules/agent-zero/main_headless.py`.
    - [ ] Implement WebSocket server using `websockets` or `fastapi` (minimal mode).

## Phase 2: Event Streaming
- [ ] **2.1: JSON Event Protocol**
    - [ ] Wrap the reasoning loop to emit JSON-formatted events (thought, action, response).
- [ ] **2.2: Daemon Manager Integration**
    - [ ] Update `nxs-agent` to point to `main_headless.py` during `start`.

## Success Criteria
- Agent starts in < 1s.
- Zero web dependencies loaded in memory at runtime.
- Verified connection from a test client.
