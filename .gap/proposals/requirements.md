# Intent: nexus-shell

## 1. Context
Nexus Shell is a modular, sovereign terminal IDE framework that orchestrates CLI/TUI tools into hot-swappable workspace compositions on tmux. The project has a working foundation (capability-adapter engine, 23+ compositions, extension system, event bus, unit tests) but key subsystems remain incomplete: the execution pipeline is stub code, the tab stacks system is unfinished, the Command Graph menu needs a full redesign, and the modeless keymap is partially wired. The idea.md defines ten pillars covering the full vision.

**Current State:** Architectural adolescence. The capabilities layer (bottom) and UI/menu layer (top) are mature. The middle execution pipeline, tab stacks, command graph, momentum restoration, and pack/profile system are incomplete or stub implementations. ~51 bash scripts handle real logic while the Python engine is partially integrated. 145 tests passing.
**Desired State:** A fully functional terminal IDE framework where all ten pillars are operational: the engine routes intents through capabilities, tab stacks provide layered navigation, the modeless keymap is fully wired, the Command Graph serves as the unified command surface, compositions and themes work with momentum persistence, packs and profiles compose independently, connectors wire tools via the event bus, and AI agents operate under sovereign governance.

## 2. Goals
Define what success looks like. Each goal should be measurable and traceable.

*   **G-01 — Unified Orchestration**: Users can launch, navigate, and manage their entire development environment through a single coherent system that orchestrates their existing CLI/TUI tools without replacing them.
*   **G-02 — Sovereign Navigation**: All workspace navigation is modeless, prefix-free, and context-aware — the user never leaves flow to interact with the system.
*   **G-03 — Indestructible Workspaces**: Workspace state survives terminal closure, machine reboot, and screen geometry changes with full fidelity.
*   **G-04 — Unified Command Surface**: Every action, setting, live status, and script in the workspace is discoverable, searchable, and executable from a single interface.
*   **G-05 — Domain Adaptability**: The system adapts to any domain of work (Python, Rust, DevOps, music, writing) through composable packs and profiles without requiring code changes.
*   **G-06 — AI as First-Class Citizen**: AI agents participate in the workspace with full context awareness while operating under human-sovereign governance.

## 3. Success Criteria (Measurable)
How will we objectively know this feature is complete? (Technology-agnostic)

*   **SC-01**: A new user can install nexus-shell and have a working IDE layout within 60 seconds.
*   **SC-02**: Pressing Alt+m opens the Command Graph workspace landing page as a new tab within 200ms.
*   **SC-03**: A workspace with 5+ panes, each with 2+ stacked tabs, can be saved and restored with all tools resuming in their correct positions.
*   **SC-04**: The Command Graph can display both static menu items and live system state (ports, processes) in a single unified view.
*   **SC-05**: A user can switch between a Python pack + DevOps profile and a Python pack + Minimalist profile without losing project state.
*   **SC-06**: An AI agent can read workspace state (pane layout, open files, running processes) via the MCP server.
*   **SC-07**: All workspace navigation keybindings (Alt+h/j/k/l, Alt+m, Alt+o, Alt+e, Alt+t, Alt+n, Alt+w, Alt+q, Alt+[, Alt+], Alt+v, Alt+s) function without a prefix key or mode switch.
*   **SC-08**: Tab rotation (Alt+[/]) cycles through stacked tabs in under 100ms with no visual glitch.
*   **SC-09**: Closing a tab (Alt+w) reveals the next tab in the stack; closing the last tab warns the user before destroying the pane.
*   **SC-10**: Closing a pane (Alt+q) destroys the container entirely, including all tabs in its stack.
*   **SC-11**: The Command Graph resolves scope cascade (workspace > profile > global) correctly when the same node ID exists at multiple levels.
*   **SC-12**: Live sources in the Command Graph resolve asynchronously and do not block menu rendering.
*   **SC-13**: Alt+o opens a capability launcher listing available modules; Enter opens as new tab, Shift+Enter replaces current tab.
*   **SC-14**: Tools with native tab support (e.g., Neovim) use their internal tab system instead of spawning duplicate stack entries.
*   **SC-15**: The per-pane tab bar correctly displays stacked tabs with the active tab highlighted, and is configurable (always/on-demand/off).

## 4. Requirements (The Source)
All requirements MUST use **EARS** (Easy Approach to Requirements Syntax).

### 4.1 Engine (Pillar 1)

*   **R-01**: **WHEN** the user dispatches an intent (verb + type + payload), **THE** system **SHALL** resolve it through the pipeline: Intent Resolver → Planner → Executor → Capability Registry → Adapter.
*   **R-02**: **WHEN** a capability type is requested and multiple adapters are registered, **THE** system **SHALL** select the highest-priority available adapter.
*   **R-03**: **IF** no adapter is available for a requested capability, **THEN THE** system **SHALL** fall back through the tiered chain (profile → discovery → hardcoded defaults) before failing.
*   **R-04**: **WHEN** an adapter is invoked, **THE** system **SHALL** pass all commands through the multiplexer's socket isolation layer, never using the default socket.

### 4.2 Universal Tab Stacks (Pillar 2)

*   **R-05**: **WHEN** a new terminal container is created (split, window, or standalone), **THE** system **SHALL** initialize it as an anonymous stack with no default role or identity.
*   **R-06**: **WHEN** the user presses Alt+n in a focused pane, **THE** system **SHALL** push a new tab onto that pane's stack without affecting other panes.
*   **R-07**: **WHEN** the user presses Alt+[ or Alt+], **THE** system **SHALL** rotate to the previous or next tab in the current stack, preserving the state of all tabs.
*   **R-08**: **WHEN** the user presses Alt+w and the focused stack has more than one tab, **THE** system **SHALL** kill only the active tab and reveal the next tab. **IF** it is the last tab, **THEN THE** system **SHALL** warn the user and offer the option to destroy the pane or cancel.
*   **R-09**: **IF** a tab is moved to the background (not visible), **THEN THE** system **SHALL** maintain it in a logical reservoir where it remains alive and recallable.
*   **R-10**: **WHEN** a user explicitly assigns a role or tag to a stack, **THE** system **SHALL** persist that identity and use it for routing intents.
*   **R-11**: **WHEN** a pane is split, **THE** system **SHALL** create a new independent stack. It **SHALL NOT** clone or inherit the parent's stack.
*   **R-12**: **IF** an adapter declares native multiplicity support (e.g., Neovim tabs/buffers), **THEN THE** system **SHALL** delegate "new instance of the same capability" requests to the tool's internal tab system rather than pushing a new stack entry.
*   **R-13**: **THE** system **SHALL** support a configurable per-pane tab bar (via pane-border-format or equivalent) that displays stacked tabs with the active tab highlighted.

### 4.3 Modeless Keymap & Navigation (Pillar 3)

*   **R-14**: **THE** system **SHALL** bind all workspace navigation to Alt+key combinations without requiring a prefix key or mode switch.
*   **R-15**: **WHEN** the user presses Alt+h, Alt+j, Alt+k, or Alt+l, **THE** system **SHALL** move focus to the pane in that spatial direction.
*   **R-16**: **WHEN** the user presses Alt+m, **THE** system **SHALL** open the Command Graph's workspace landing page as a new tab in the current pane.
*   **R-17**: **WHEN** the user presses Alt+o, **THE** system **SHALL** open a capability launcher submenu listing available modules (editor, terminal, chat, explorer, menu, etc.) in the current pane.
*   **R-18**: **WHEN** the user selects a module in the capability launcher and presses Enter, **THE** system **SHALL** open that module as a new tab. **WHEN** the user presses Shift+Enter, **THE** system **SHALL** replace the current tab with the selected module.
*   **R-19**: **WHEN** the user presses Alt+e on a listed module in the capability launcher, **THE** system **SHALL** present the adapter configuration for that capability — listing available tools and allowing the user to set a new default or spawn a specific tool without changing the default.
*   **R-20**: **WHEN** the user presses Alt+t, **THE** system **SHALL** display a submenu listing active tabs in the current pane's stack.
*   **R-21**: **WHEN** the user presses Alt+q, **THE** system **SHALL** destroy the focused pane entirely, including all tabs in its stack.
*   **R-22**: **WHEN** the user presses Alt+v or Alt+s, **THE** system **SHALL** split the focused pane vertically or horizontally, creating a new anonymous stack in the new container.
*   **R-23**: **THE** Enter/Shift+Enter convention **SHALL** be consistent across the entire system: Enter opens the selection as a new tab; Shift+Enter replaces the current tab with the selection.

### 4.4 Command Graph / Menu (Pillar 4)

*   **R-24**: **THE** system **SHALL** represent all menu items as nodes with one of four types: Action, Group, Live Source, or Setting.
*   **R-25**: **WHEN** a node of type Action is selected and Enter is pressed, **THE** system **SHALL** execute the node's command, opening the result as a new tab. **WHEN** Shift+Enter is pressed, **THE** system **SHALL** execute the command replacing the current tab.
*   **R-26**: **WHEN** a node is selected and Opt+E is pressed, **THE** system **SHALL** open the node's source (script, config, or command definition) in a new editor tab.
*   **R-27**: **WHEN** the Command Graph renders, **THE** system **SHALL** resolve node scope by merging workspace over profile over global, with workspace taking precedence.
*   **R-28**: **IF** a node has type Live Source, **THEN THE** system **SHALL** resolve it asynchronously at render time with a configurable timeout, and **SHALL NOT** block rendering of static nodes.
*   **R-29**: **WHEN** a user types "/" in the Command Graph, **THE** system **SHALL** filter all visible nodes by label, tag, or command content.
*   **R-30**: **THE** system **SHALL** allow users to define custom node trees in YAML that appear in the Command Graph alongside system nodes.
*   **R-31**: **WHEN** a node is selected and the user presses l or Right, **THE** system **SHALL** expand into the node's submenu or list available adapters for direct spawning.
*   **R-32**: **IF** a node has type Setting, **THEN THE** system **SHALL** point to a configuration file. Opt+E **SHALL** open that file in the editor for modification.
*   **R-33**: **THE** Menu capability **SHALL** have a null adapter that provides graceful degradation when no menu renderer (fzf, gum, Textual) is available.

### 4.5 UI Layer (Pillar 5)

*   **R-34**: **WHEN** a composition is selected, **THE** system **SHALL** build the specified pane layout with all declared tools launched in their assigned positions.
*   **R-35**: **THE** system **SHALL** support switching between compositions on a running workspace without destroying session state in unaffected panes.
*   **R-36**: **THE** system **SHALL** provide a real-time HUD that aggregates telemetry from registered modules and displays it as a single status line.
*   **R-37**: **WHEN** a theme is selected, **THE** system **SHALL** apply its color tokens to the HUD, tmux status line, and shell prompt.

### 4.6 Momentum / Session Persistence (Pillar 6)

*   **R-38**: **WHEN** the user saves a workspace (explicitly or on detach), **THE** system **SHALL** capture: pane layout geometry, running commands, working directories, tab stack contents, roles, and identities.
*   **R-39**: **WHEN** a saved workspace is restored, **THE** system **SHALL** use deferred layout application — applying geometry after the terminal is attached at its real size.
*   **R-40**: **WHEN** restoring to a different screen geometry than the saved state, **THE** system **SHALL** use proportional coordinates to map panes to their closest correct positions.
*   **R-41**: **WHEN** momentum restoration reconnects panes to logical stacks, **THE** system **SHALL** match by identity (role, UUID), not by physical pane index.

### 4.7 Packs & Profiles (Pillar 7)

*   **R-42**: **WHEN** a project is opened and recognized markers are present (e.g., pyproject.toml, Cargo.toml), **THE** system **SHALL** suggest available packs but **SHALL NOT** enable them without explicit user confirmation.
*   **R-43**: **WHEN** a pack is enabled, **THE** system **SHALL** register its tools, connectors, services, and Command Graph nodes into the workspace scope.
*   **R-44**: **WHEN** a pack is disabled, **THE** system **SHALL** remove its registered nodes and stop its services without affecting other packs or the base workspace.
*   **R-45**: **WHEN** a profile is selected, **THE** system **SHALL** apply its composition, HUD modules, keybind overrides, and theme preferences.
*   **R-46**: **THE** system **SHALL** allow packs and profiles to be composed independently — changing a profile **SHALL NOT** disable active packs, and vice versa.

### 4.8 Module Layer (Pillar 8)

*   **R-47**: **THE** system **SHALL** provide an MCP server that exposes workspace state (pane layout, open files, running processes, active roles) to AI models.
*   **R-48**: **WHEN** a file is opened or viewed, **THE** system **SHALL** route it to the best available renderer based on file type (markdown → formatter, mermaid → diagram renderer, code → syntax highlighter).
*   **R-49**: **THE** system **SHALL** support connectors — lightweight event bus subscribers that wire cross-tool behaviors (e.g., editor save → test run, test fail → editor jump).

### 4.9 Event Bus (Pillar 9)

*   **R-50**: **THE** system **SHALL** provide an async pub/sub event bus over Unix domain sockets with typed events (filesystem, test, editor, AI, UI).
*   **R-51**: **WHEN** an event is published, **THE** system **SHALL** deliver it to all active subscribers within 50ms.
*   **R-52**: **IF** a subscriber becomes unreachable, **THEN THE** system **SHALL** detect and remove the dead subscriber without affecting other subscribers.
*   **R-53**: **THE** system **SHALL** maintain a circular event history (minimum 1000 events) for late-joining subscribers and debugging.

### 4.10 Sovereign AI Governance (Pillar 10)

*   **R-54**: **THE** system **SHALL** enforce separation of powers: AI agents propose changes, human supervisors approve, execution occurs in isolation.
*   **R-55**: **WHEN** an AI agent's proposal is approved, **THE** system **SHALL** execute it in a sandboxed environment with process-level isolation.
*   **R-56**: **IF** a specification has been approved and locked, **THEN THE** system **SHALL** reject any agent attempt to overwrite it.
*   **R-57**: **THE** system **SHALL** expose workspace context to AI agents via the MCP server, enabling context-aware assistance without granting direct workspace modification rights.

## 5. Assumptions & Risks

### Assumptions
*   **A-01**: The target platform is macOS and Linux with tmux 3.2+ as the primary multiplexer.
*   **A-02**: Users have a terminal emulator that supports Alt/Option key passthrough (iTerm2, Alacritty, Kitty, WezTerm).
*   **A-03**: Python 3.10+ and a POSIX shell (zsh or bash) are available on the host system.
*   **A-04**: Users are comfortable with terminal-based workflows and do not require GUI fallbacks.

### Risks
*   **RK-01**: Alt key conflicts with macOS system shortcuts or terminal emulator bindings may prevent modeless navigation from working out of the box. **Mitigation**: provide a keybind configuration system with profile presets.
*   **RK-02**: Live source resolution in the Command Graph may introduce latency or hang the menu if external services are slow. **Mitigation**: enforce async resolution with configurable timeouts and caching.
*   **RK-03**: The dual bash/Python execution path creates maintenance burden and inconsistent behavior. **Mitigation**: consolidate to Python engine as the single execution path.
*   **RK-04**: Momentum restoration may fail for tools that don't support headless resume (e.g., TUI apps that require a TTY). **Mitigation**: re-launch commands rather than resume processes, with state hints where possible.

---
**The Compliance Chain**:
These Requirements are the **primary source**. Every Design Property must validate at least one of these, and every Task must implement at least one Property.
