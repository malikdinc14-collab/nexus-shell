# Idea: Web Surface + Web Module

## Problem Statement

Nexus Shell currently runs exclusively on tmux. The adapter architecture is in place (all surface operations go through capability ABCs), but only one surface implementation exists. To prove the portability guarantee — that extensions, packs, and user config work identically across surfaces — a second surface is needed.

## Why Web First

1. **Proves the hybrid model** — embedding real terminal processes (nvim, yazi, zsh) via xterm.js in a non-terminal surface validates the "wrap, don't replace" principle.
2. **Becomes Tauri for free** — Tauri IS a web view + native shell. Build the web rendering layer first, wrap it in Tauri later.
3. **Remotely accessible** — access workspaces from any browser, any device.
4. **Forces clean separation** — if the engine can drive a browser over WebSocket, the Surface ABC is proven correct.

## Two Distinct Components

### 1. Web Module (Server-Side — `core/engine/capabilities/adapters/web/`)

The server-side bridge between the Nexus engine and the browser. This is a **capability module**, not a surface.

Responsibilities:
- **WebSocket server**: Bidirectional communication with browser clients
- **PTY manager**: Spawn and manage pseudo-terminal processes server-side
- **State sync**: Push workspace state (layout, tabs, HUD) to connected clients
- **Event bridge**: Route engine events to browser, browser actions to engine
- **Auth**: Token-based authentication for remote sessions

This module runs alongside the engine regardless of surface — it's what makes the workspace accessible over the network.

### 2. Web Surface (Browser-Side — frontend app)

The browser application that renders the workspace. Implements the visual layer.

Responsibilities:
- **Panel layout**: CSS grid/flexbox geometry management
- **Terminal rendering**: xterm.js widgets for each pane hosting a PTY
- **Command palette**: Native browser UI replacing fzf-tmux
- **HUD**: DOM-based status bar with live source data
- **Tab bar**: Per-pane tab strip with push/pop/rotate
- **Keybindings**: Alt+* keymap translated to WebSocket messages

### Architecture

```
Browser (frontend)              Server (backend)
+----------------------+        +----------------------+
| React / Svelte       | <----> | Web Module            |
| xterm.js panels      |  WS    |   WebSocket server    |
| CSS grid layout      |        |   PTY manager         |
| Command palette      |        |   State sync          |
| Tab bar / HUD        |        |   Event bridge        |
+----------------------+        +----------------------+
                                         |
                                         | Surface ABC / Capability ABCs
                                         v
                                +----------------------+
                                | NexusCore (unchanged) |
                                | State, Bus, Config,   |
                                | Graph, Packs          |
                                +----------------------+
```

### The Hybrid Terminal Model

The web surface wraps CLI tools — it doesn't replace them:

- nvim runs as a real process server-side, rendered via xterm.js
- yazi runs as a real process, rendered via xterm.js
- zsh runs as a real process, rendered via xterm.js
- EditorCapability adapter talks to nvim via RPC — unchanged from tmux surface
- The browser is a viewport, not a reimplementation

Future option: native browser panels (Monaco for editor, custom file browser) can be offered as alternative adapters. User chooses via `adapters.yaml`. But the default and recommended path is embedded terminals.

## Key Design Decisions

- **WebSocket, not HTTP polling** — real-time bidirectional communication
- **Server-side PTY, not client-side** — processes run on the machine, browser renders output
- **xterm.js for terminal rendering** — battle-tested, used by VS Code, Theia, etc.
- **Same keybinding model** — Alt+* works identically in browser
- **Auth required for remote** — localhost can be unauthenticated, remote requires token

## Target User

- Developers wanting remote workspace access from any browser
- Users wanting a native-feel app (via Tauri wrapper, later)
- Testing and CI (headless browser surface for automated validation)

## Relationship to Tauri (Phase 7)

The web surface IS the rendering layer for the future Tauri desktop app. Tauri wraps a web view and adds native window management. Building web first means:
- Phase 5: Web surface works in any browser
- Phase 7: Same web frontend wrapped in Tauri, with native PTY hosting via Rust instead of server-side Python

## Overnight Task Potential

This phase is a strong candidate for overnight autonomous execution if planned thoroughly enough:
- Interface contracts are well-defined (Surface ABC, WebSocket protocol)
- Components are independently testable (PTY manager, WebSocket server, frontend panels)
- ISC can be made binary and granular
