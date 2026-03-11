# Requirements: Agent Zero Headless Migration

## 1. Intent & Scope
**Intent**: Decouple the Agent Zero reasoning engine from its Gradio web UI.
**Scope**: Modifying entry points, ensuring CLI-friendly logging, and standardizing the API for `nxs-agent` and `pi` frontend consumption.

## 2. Core Principles
1. **Lightweight Purity**: No web server (Gradio/FastAPI) should run unless explicitly requested for debugging.
2. **Standardized I/O**: The agent must consume input via stdin/sockets/JSON and output structured events.

## 3. Functional Requirements
- **3.1**: Create a `main_headless.py` or similar entry point in the Agent Zero module.
- **3.2**: Implement a standard WebSocket or TCP server for real-time conversational streaming.
- **3.3**: Ensure all "Tool Execution" output is redirected to the daemon logs rather than the console (unless in Follow Mode).

## 4. Acceptance Criteria
- Agent Zero can be started via `./daemon_manager.sh start agent-zero "python main_headless.py"` without spawning a web browser or opening a Gradio port.
- The `pi` frontend can establish a stable connection to this headless service.
