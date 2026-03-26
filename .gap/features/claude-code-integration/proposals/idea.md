# Idea: Claude Code Integration (The Cockpit)

## Problem Statement
Claude Code runs in a terminal pane but nexus-shell has no visibility into what it's doing. Users can't see Claude's tool calls, file edits, or status from other panes or the HUD. There's no way to trigger actions based on Claude's activity.

## Proposed Solution
Deep integration between nexus-shell and Claude Code via hooks, a bridge module, and a follow pane that provides real-time visibility into Claude Code sessions.

## Key Features
- **Follow Pane**: Dedicated pane showing a clean, formatted stream of Claude's tool calls and file edits in real-time.
- **HUD Module**: Status bar indicator showing Claude state (idle/thinking/tool_use), current file, cost, and token count.
- **Event Bridge**: PostToolUse hook writes structured events to JSONL; bridge module translates to nexus typed events.
- **Auto-Connectors**: Event-driven automation — e.g., `claude.file_edit:*.py` triggers test runs.
- **Claude as Capability**: First-class `AgentCapability` adapter for Claude Code.
- **Context Injection**: Feed workspace-relevant files to Claude via embeddings (see workspace-indexing feature).

## Architecture
```
Claude Code session (interactive)
    │
    │ PostToolUse hook (every tool call)
    ▼
/tmp/nexus/claude/{session_id}.jsonl
    │
    │ Tail + parse
    ▼
core/engine/bridges/claude_code.py
    │
    ├──► Event bus (claude.* events)
    ├──► HUD module (status, cost)
    ├──► Follow pane renderer
    └──► Connectors (auto-test, notifications)
```

## Integration Points
- Claude Code hooks (PostToolUse, SessionStart, SessionEnd, Stop)
- Event bus (core/engine/bus/enhanced_bus.py)
- HUD module framework (core/engine/hud/)
- Connector engine (core/engine/connectors/)
- Capability registry (AgentCapability adapter)

## Target User
Any developer using Claude Code who wants live visibility and automation within their workspace.
