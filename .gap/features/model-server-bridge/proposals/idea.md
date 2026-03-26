# Idea: Model-Server Bridge (AI Infrastructure Integration)

## Problem Statement
The model-server at `localhost:8080` manages local AI model slots with SSE events, budget enforcement, and hot-swap. Nexus-shell has no visibility into this — users must manually check model status, costs, and health.

## Proposed Solution
A bridge module (`core/engine/bridges/model_server.py`) that connects to the model-server's SSE stream, translates events into typed nexus events, and surfaces them through HUD modules and the Command Graph.

## Key Features
- **SSE → Event Bus bridge**: Persistent connection to `GET /v1/events`, translating model-server events to nexus typed events (`ai.slot.*`, `ai.usage.*`, `ai.health.*`).
- **HUD: model status**: Live display of active slots, model names, and status indicators (green/yellow/red).
- **HUD: cost tracker**: Running USD cost and token counts from `slot.usage` events.
- **HUD: health heartbeat**: Green dot when connected, red when SSE drops. Based on `system.health` (30s interval).
- **Command Graph nodes**: Menu commands for slot create, pause, resume, swap, kill.
- **Slot-aware routing**: Maintain "current model" per workspace. `nexus ask` routes to the active slot via `X-Bucket-Group` header.
- **Budget/error connectors**: `budget.exhausted` and `slot.error` trigger desktop notifications.
- **Auto-slot lifecycle**: Slots created via boot lists auto-kill on workspace detach.

## API Contract
- Base URL: `http://localhost:8080`
- SSE: `GET /v1/events`
- Control: `POST /v1/slots/{id}/pause|resume|swap`, `DELETE /v1/slots/{id}`
- Status: `GET /status`, `GET /health`
- Full spec: `/tmp/model-server-integration.md`

## Integration Points
- Event bus (`core/engine/bus/enhanced_bus.py`)
- HUD module framework (`core/engine/hud/`)
- Command Graph (`core/engine/graph/`)
- Connector engine (`core/engine/connectors/`)
- Boot lists (`.nexus/boot.yaml`)

## Target User
Developers running local AI models who want live visibility and control from their workspace.
