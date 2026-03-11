# Design: Agent Zero Headless Migration

## 1. System Architecture

### 1.1 Modularity
We will move the core reasoning loop into a reusable Class/Module structure if not already present, separating it from `main.py` (which contains Gradio logic).

### 1.2 Communication Layer
We will implement a simple **JSON-RPC over WebSockets** interface:
- **Input**: `{ "action": "chat", "message": "...", "context": { ... } }`
- **Output**: `{ "type": "thought", "content": "..." }`, `{ "type": "tool_start", "tool": "bash" }`, etc.

## 2. Component Design

### 2.1 Entry Point (`main_headless.py`)
A thin wrapper that:
1. Loads settings from `usr/settings.json`.
2. Initializes the `AgentZero` core instance.
3. Starts a WebSocket server on a configurable port (default 5000).

### 2.2 Telemetry Hook
Integrate a hook that writes the agent's current "Thought" and "Action" to a temporary file (`/tmp/nexus/agent_state.json`) for the native Nexus status line.
