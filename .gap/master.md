# Nexus Shell: Master Specification

This is the central index for the **Gated Agent Protocol (GAP)** and all documented features of the Nexus Shell.

## Core Foundations
- [**System Taxonomy**](taxonomy.md) - Unified terminology and concepts.
- [**Architecture Theory**](architecture.md) - Three-layer model, extension hierarchy, hybrid surface model, content provider contracts.
- [**Structural Design**](design.md) - Data models, interface contracts, configuration architecture.
- [**Roadmap**](../docs/plans/ROADMAP.md) - Living roadmap (legacy — see phases below for current plan).

---

## Completed

### Phase 1-3: Core Engine & Adapter Architecture
- Capability adapter framework (Neovim, Yazi, fzf, gum, Textual, OpenCode, tmux)
- Adapter invariant enforced — no direct surface calls outside adapters
- Tab stacks, event bus, config cascade, pack detection
- Unified CLI (`nexus-ctl`) with dispatch system
- tmux surface (23 compositions, modeless Alt+* keybindings)
- 692+ passing tests

### Navigation & Orchestration
- [**Universal Tab Stacks**](features/tabs/vision.md) - Platform-agnostic stack management.
- [**Status HUD**](features/status-hud/proposals/idea.md) - Real-time system feedback.
- [**Menu V2**](features/menuv2/implementation_plan.md) - Command palette and menu system.

---

## Phase 4: Hardening & Local Features

### 4-Foundation: Spec Hardening *(NEW — addresses architectural gaps)*

> These specs must be written before Phase 5. They define the runtime contracts that make everything above the engine portable and predictable. No code — pure specification.

- [**4-F1: Execution Model**](specs/execution-model.md) — State ownership, workspace lifecycle, event ordering, provider execution timing, failure semantics.
- [**4-F2: Content Provider Contract**](specs/content-provider.md) — ContentProvider abstraction, MenuNode JSON schema, provider implementations (shell/Python/RPC/YAML), validation, timeouts, portability tiers.
- [**4-F3: Pack Governance**](specs/pack-governance.md) — Expressiveness limits, strict schema, the Ansible trap prevention, pack lifecycle, isolation rules.

### 4A: Project-Local Configuration
- [**Boot Lists**](features/boot-lists/proposals/idea.md) - `.nexus/boot.yaml` auto-execution on workspace attach.
- [**Project Profiles**](features/project-profiles/proposals/idea.md) - Role-based environment presets.
- [**Nexus Vault**](features/nexus-vault/proposals/idea.md) - Encrypted project secrets.

### 4B: External Intelligence
- [**Model-Server Bridge**](features/model-server-bridge/proposals/idea.md) - SSE bridge, HUD, slot control for AI model gateway.

### 4C: Module Ecosystem
- [**Module System**](features/module-system/proposals/idea.md) - Install UX, pack enrichment, registry.

### 4D: Code Intelligence
- [**LSP Integration**](features/lsp-integration/proposals/idea.md) - Classical LSP + AI-powered completions.
- [**Jump to Definition**](features/jump-to-definition/proposals/idea.md) - Cross-platform symbol resolution.
- [**Headless DAP**](features/headless-dap/proposals/idea.md) - Debug Adapter Protocol.

### 4E: Infrastructure
- [**Notification System**](features/notification-system/proposals/idea.md) - Desktop notifications with urgency levels.
- [**Testing Suite**](features/testing-suite/status.yaml) - Property-based and unit testing framework.

---

## Phase 5: Web Surface & Multi-Surface

> The phase that proves the architecture. If the engine can drive a browser, it can drive anything.

### 5A: Web Module (Server-Side Bridge)
- WebSocket server (asyncio + websockets)
- PTY manager — spawn, multiplex, stream terminal I/O to clients
- State sync protocol — push workspace layout, tabs, HUD to connected browsers
- Event bridge — engine events → WebSocket, client actions → engine
- Auth — token-based for remote, unauthenticated for localhost
- **Testable output:** connect with `websocat` or minimal HTML page, see terminal streaming

### 5B: Web Surface (Browser Frontend)
- [**WebSurface**](features/web-surface/proposals/idea.md) - Browser-based workspace rendering.
- Panel layout engine (CSS grid, drag-to-resize)
- xterm.js terminal widgets (one per pane, connected to server PTYs)
- Command palette (native browser UI replacing fzf-tmux)
- Tab bar per pane (push/pop/rotate via UI + keyboard)
- HUD (DOM status bar with live source data)
- Alt+* keybinding translation
- `WebMultiplexerAdapter` implementing MultiplexerCapability
- **Testable output:** full Nexus workspace in a browser — navigate, run commands, interact with nvim

### 5C: Renderer Capability (General-Purpose Viewports)
- New capability type: `RendererCapability` — panes can host any content type, not just terminals
- Content type adapters: terminal, markdown, web page, PDF, image, 3D (future)
- Interactive renderers: click, scroll, navigate within the viewport
- Tab stacks can mix types: terminal tab + markdown preview + web view in same pane
- On tmux: degrades to terminal tools (glow, w3m, chafa)
- On web/Tauri: native rendering (HTML, iframe, PDF.js, WebGL)
- **This is what makes Tauri compelling** — not "tmux in a window" but a workspace where panes host different content types

### 5-Other
- [**Workspace Engine**](features/workspace-engine/proposals/idea.md) - Multi-folder workspace aggregation.
- [**Session Recording**](features/session-recording/proposals/idea.md) - Capture and replay terminal sessions.

---

## Phase 6: Pack Ecosystem & Intelligence

### 6A: Domain Packs
- python-dev, rust-dev, writing, devops, music-production packs
- Pack install/discovery (`nexus pack install`)
- Connector system — event-to-action automation wiring
- Community pack registry (future)

### 6B: Sovereign Intelligence
- [**Composition Designer**](features/composition-designer/proposals/idea.md) - Visual layout builder.
- [**Ascent Space**](features/ascent-space/proposals/idea.md) - Recursive agency and agent orchestration.
- [**Conflict Matrix**](features/conflict-matrix/proposals/idea.md) - System invariant resolution.
- [**PI Frontend**](features/pi-frontend/idea.md) - Protocol Interface frontend.

---

## Phase 7: Native App — Nexus Desktop

> Tauri wraps the web surface. Build web first (Phase 5), wrap in native shell here.

- **7A: Tauri Host** — macOS-first native app wrapping web surface, Rust PTY backend replacing Python PTY, `NexusDesktopSurface`
- **7B: Native Renderers** — WebView panels for markdown/web/PDF, GPU-accelerated terminal via native terminal widget
- **7C: Visual Theming** — Background images, pane transparency, vibrancy/blur, theme engine
- **7D: Linux Native Path** — WM orchestrator mode (Sway/Hyprland IPC) as alternative to self-contained app

---

## Overnight Task Mapping

> Phases annotated by autonomous execution potential. The goal: plan thoroughly enough that agents can execute overnight.

| Phase | Overnight-able? | Reasoning |
|-------|----------------|-----------|
| 4-Foundation (Specs) | No | Requires human design decisions |
| 4A-4E (Features) | Partially | Boot lists, vault are mechanical; LSP needs judgment |
| 5A (Web Module) | **Yes** | WebSocket server, PTY manager are well-defined mechanical work |
| 5B (Web Frontend) | Partially | Core rendering mechanical; UX polish needs judgment |
| 5C (Renderer) | **Yes** | ABC + first adapters follow established pattern |
| 6A (Packs) | **Yes** | Each pack is independent YAML + validation |
| 6B (Intelligence) | No | Design-heavy, needs human direction |
| 7A (Tauri) | Partially | Wrapping is mechanical; native integration needs decisions |
| 7B-7D | No | Design and UX judgment required |

**The pattern:** Phase 4-Foundation specs are the investment that makes Phases 5-7 overnight-executable. More precise contracts → more autonomous agent work.

---

## Archives
- [**Nexus Shell V1**](features/nexus-shell-v1/vision.md) - Historical architecture notes.
