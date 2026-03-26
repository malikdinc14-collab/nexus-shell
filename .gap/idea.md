# Idea: nexus-shell

## 1. The Core Concept
Nexus Shell is a **modular, sovereign terminal IDE framework** that transforms tmux into a spatial computing canvas for developers and creative professionals.

Rather than being yet another terminal multiplexer, Nexus Shell is an **orchestration engine** — it arranges your favorite CLI/TUI tools (Neovim, Yazi, fzf, OpenCode, lazygit, btop, and dozens more) into hot-swappable, indestructible workspace layouts called **compositions**. Each composition is a JSON-defined arrangement of panes, roles, and commands that can be switched instantly without losing state.

The architecture follows a **Bring Your Own Tools** philosophy: Nexus provides the intelligent wiring; you bring the tools you already love.

### Ten Pillars of the System (Three Layers: Tools + Connectors + Services)

1. **The Engine** — A capability-adapter framework where abstract capabilities (Editor, Explorer, Multiplexer, Agent, Menu) are fulfilled by concrete adapters (Neovim, Yazi, tmux, OpenCode, fzf). The engine handles intent resolution, execution planning, and state management through a clean pipeline: User Intent → Intent Resolver → Planner → Executor → Capability Registry → Adapter.

2. **Universal Tab Stacks** — The spatial navigation model that governs how users move between and within containers. Every terminal container — whether a tmux pane, a standalone window, or a future GUI tab — holds a **stack of tabs**: multiple tools layered on top of each other that the user can rotate through without losing context or state. A single pane might hold an editor, a shell, and a menu, all stacked and instantly switchable.

   Three principles define the navigation philosophy:
   - **Identity-Free Initialization** — containers start as anonymous canvases. No default role, no automatic slot assignment. The user decides what a stack is "for" by explicit action, not by inheritance.
   - **Focus Sovereignty** — actions always execute where the user is looking. Tool creation, tab rotation, and identity assignment all follow focus, never redirect it.
   - **Platform Agnosticism** — the logical stack model is decoupled from the physical multiplexer. The same navigation experience works whether you're in tmux, standalone terminal windows, or future GUI shells. Identity follows content, not container.

   Inactive tabs live in a **logical reservoir** — they remain alive in the background without requiring a visible container, and can be recalled to any pane at any time. Session restoration uses **geometric anchors** (proportional screen coordinates) rather than physical IDs, meaning layouts restore correctly across different screen sizes and monitor configurations.

   **Native Tab Delegation** — Tools that support their own internal tab/buffer systems (e.g., Neovim tabs and buffers) are not duplicated as separate stack entries. Instead, the capability-adapter contract declares whether an adapter supports native multiplicity. When it does, requests for "another instance of the same capability" delegate to the tool's internal tab system rather than pushing a new entry onto the pane stack. The pane stack is for layering *different* tools — not for duplicating tools that already handle multiplicity natively.

   **Tab Bar** — Each pane can optionally display a visual tab indicator (e.g., `[e(ditor)] [c(hat)] [t(erminal)]`) showing stacked tabs with the active one highlighted. This renders per-pane via tmux's pane-border-format. The tab bar is configurable — users can enable it always, on-demand, or disable it entirely.

   **Last-Tab Safety** — Closing the last tab in a stack (Alt+w) triggers a warning rather than silently destroying the pane or leaving an empty shell. The user is given the option to proceed (destroying the pane) or cancel. This prevents accidental pane destruction while respecting user sovereignty — warn, never refuse.

3. **Modeless Keymap & Navigation** — Nexus Shell rejects the prefix-key model (tmux's Ctrl-b) and modal navigation entirely. Instead, **Alt (Option) is the universal spatial modifier** — every workspace action is one keystroke away, always available, in any context.

   The core keybindings:
   - **Alt+h/j/k/l** — move focus between panes (spatial, vim-style)
   - **Alt+m** — **Menu**: opens the Command Graph's workspace landing page as a new tab in the current pane. This is the front door to the entire command surface — actions, settings, live sources, everything.
   - **Alt+o** — **Open (Capability Launcher)**: opens a submenu listing available capabilities/modules (editor, terminal, chat, menu, explorer, etc.) in the current pane. Enter on a module opens it as a new tab. Shift+Enter replaces the current tab with the selected module. This submenu is itself rendered by the Menu capability, making menus composable and recursive.
   - **Alt+e** — **Edit Adapter** (within the capability launcher): on any listed module, opens the adapter configuration — lists available tools for that capability and lets the user choose a new default or spawn a specific tool without changing the default. For example, Alt+e on "Editor" shows neovim, helix, micro, etc. Enter sets the default; navigating right (l/Right) expands the list for one-shot spawning without changing the default.
   - **Alt+t** — **Tab Manager**: lists active tabs in the current pane's stack as a submenu. Jump to a tab, reorder, or close from here.
   - **Alt+n** — push a new tab onto the current stack
   - **Alt+w** — kill the active tab in the focused stack (warns if it's the last tab; the user can override to destroy the pane)
   - **Alt+q** — kill the entire pane, including all tabs in its stack
   - **Alt+[** / **Alt+]** — rotate left/right through tabs in the current stack
   - **Alt+v** — split pane vertically
   - **Alt+s** — split pane horizontally

   **Enter / Shift+Enter Convention** — This convention generalizes across the entire system: **Enter** opens the selected item as a new tab in the current stack. **Shift+Enter** replaces the current tab with the selected item. This applies in the Command Graph (Enter on a script = new terminal tab running it), in the capability launcher (Enter = new tab, Shift+Enter = replace), and anywhere else a selection produces a new view.

   The distinction between Alt+w (kill tab) and Alt+q (kill pane) is deliberate and critical — it maps directly to the Tab Stacks model. Closing a tab returns you to the next layer in the stack; closing a pane destroys the container entirely.

   **Null Adapter for Menu** — Since the Menu is itself a capability (with fzf, gum, Textual as adapters), a null adapter is provided for graceful degradation when no menu renderer is available — mirroring the null multiplexer adapter pattern. This also enables the menu to render itself as a tab via its own capability, which is what makes Alt+o and Alt+m work: they spawn menu instances as stack entries.

4. **The Command Graph (Menu)** — The central nervous system of the entire IDE. Not a simple list — a **unified command surface** where everything actionable or observable is represented as a node in a dynamically resolved, scoped command tree. The menu is simultaneously a control center (all settings), a launcher (all actions), an observatory (live system state), and a user-extensible interface builder (custom menus and submenus). It is the single entry point for configuring the IDE, managing profiles, controlling workspaces, and monitoring active status.

   The command graph operates on a **node model** with four fundamental types:
   - **Action** — executes a command, script, or system operation (shell, Python, internal, navigation)
   - **Group** — a container of nodes supporting arbitrary nesting (submenus, categories)
   - **Live Source** — a dynamic generator that resolves nodes at render time from system state (active ports, running instances, open tabs, service health)
   - **Setting** — a configurable value in the system (toggles, paths, strings, selections)

   Every node lives within a **three-tier scope cascade** modeled after VSCode's settings hierarchy:
   - **Global** — user-wide defaults
   - **Profile** — context-specific overrides (dev, ML, ops, music, writing)
   - **Workspace** — project-specific configuration (always wins)

   Resolution order: workspace overrides profile overrides global. Nodes merge by ID; groups can extend children or disable inherited entries.

   The interaction model is deliberately minimal:
   - **Enter** — execute the selected node (opens result as a new tab — e.g., a script runs in a new terminal tab)
   - **Shift+Enter** — execute the selected node, replacing the current tab (the menu tab transforms into the result)
   - **Opt+E** — open the node's source (script, command, or config file) in a new editor tab for full editing
   - **Arrow keys / j/k** — navigate
   - **l / Right** — expand into a submenu or list (e.g., on a capability node, shows available adapters for direct spawning)
   - **Space** — expand/collapse groups
   - **/** — filter and search by label, tag, or command

   The Opt+E behavior is critical: it externalizes all editing to the real editor (Neovim tab), meaning any script, action, or setting can be modified with full editor power — syntax highlighting, LSP, the works.

   **Settings in v1 are files.** Setting nodes in the Command Graph point to configuration files. Opt+E opens them in the editor. No inline menu editing is needed — the menu is the discovery and navigation layer, the editor is the editing layer. This keeps v1 simple while preserving the full power of the editor for configuration.

   Live sources are **not stored** — they are resolved asynchronously at render time with timeouts and caching. This means the menu can show active ports, running containers, GPU instances, open editor tabs, and service mesh health alongside static actions and scripts, all in one unified interface.

   Users can author their own interface by defining custom node trees in YAML — arbitrary menus for notes, quick actions, bookmarked directories, build commands, model loaders, or anything else.

5. **The UI Layer** — 23+ pre-built compositions (IDE-like, AI-pair, music studio, DevOps, school, sovereign-control, and more), 6 themes, a real-time HUD with telemetry modules (tabs, token burn, dock, mesh, music, ascent), and the hierarchical YAML-driven menu system that feeds into the Command Graph.

6. **Momentum (Session Persistence)** — Nexus Shell workspaces are **indestructible**. Close your terminal, reboot your machine, come back tomorrow — everything is exactly where you left it. Momentum is the high-fidelity session persistence engine that captures the complete state of your workspace: pane layout geometry, running commands, working directories, tab stack contents, roles, and identities.

   Restoration is not a crude "re-split panes and re-run commands." Momentum captures the precise layout string and uses **deferred restoration** — the layout is applied after the terminal is attached at its real size, preventing the distortion that happens when restoring into a different terminal geometry. Panes are reconnected to their logical stacks via identity, not physical index.

   Combined with the geometric anchors from Tab Stacks, this means: save on a 4K monitor, restore on a laptop — the proportions adapt, the tools resume, the workspace lives.

7. **Packs & Profiles (the Two-Axis Model)** — Where traditional IDEs like VSCode use a single "extension" concept for everything, Nexus Shell separates two fundamentally different concerns:

   **Packs** answer: *"What does this project need?"* A pack is a declared bundle of tools, connectors, services, and Command Graph nodes for a specific domain of work. A Python pack brings an ipython REPL, pytest wiring, editor↔REPL send-selection connector, test-result→editor jump-to-error connector, and menu actions like "Run Tests" and "Select Venv." A Rust pack brings cargo-watch, bacon error dashboard, and build-on-save wiring. A Kubernetes pack brings k9s, helm, and cluster health live sources.

   Critically, packs do NOT inject capabilities into the editor the way VSCode extensions do. The tools already exist as complete, standalone programs. Packs declare which tools to use, how to connect them, and what services to run — the intelligent wiring between already-complete tools.

   Pack activation follows a strict sovereignty model: **detect, suggest, never auto-enable**. Nexus reads project markers (pyproject.toml, Cargo.toml, Dockerfile) and suggests available packs, but nothing activates without explicit user consent. Once enabled, the choice persists in workspace config.

   **Profiles** answer: *"How do I like to work?"* A profile is a declared arrangement of compositions, HUD modules, keybinds, and aesthetic preferences for a specific way of working. A DevOps profile emphasizes monitoring and multi-cluster layouts. A Minimalist profile strips everything to editor + terminal. A Music Production profile activates visualizers and BPM tracking.

   The two axes compose independently: Python pack + DevOps profile = Python infrastructure scripts with monitoring-heavy layout. Python pack + Data Science profile = notebooks with visualization panes. Same project capabilities, different work styles.

8. **The Module Layer** — First-party integrations including a Model Context Protocol server (exposing Nexus state to AI models), a multi-tier menu engine (fzf/gum/Textual renderers for the Command Graph), agent bootstrapping with proxy routing, and a smart content renderer that dispatches files to their best terminal viewer. The module layer also hosts **connectors** — lightweight event bus wires that bridge tools (e.g., "editor saves file → tests auto-run," "test fails → editor jumps to error line"). Connectors are the nexus-shell equivalent of extension integrations, but they are thin glue between complete tools rather than monolithic plugins.

9. **The Event Bus** — An async pub/sub system over Unix domain sockets enabling real-time inter-pane communication with typed events (filesystem changes, test results, editor state, AI responses, UI focus). This is the wiring that makes live sources in the Command Graph possible and enables cross-pane intelligence.

10. **Sovereign AI Governance** — A principled governance layer for autonomous AI agents operating within the workspace. Enforces separation of powers between reasoning and execution through a gated alignment workflow: agents propose, supervisors approve, execution happens in sandboxed isolation. Spec locks ensure approved designs are immutable. This allows AI to be a first-class citizen in the workspace while maintaining human sovereignty over critical decisions.

## 2. Problem Statement
Modern developers juggle an ever-growing ecosystem of specialized terminal tools — editors, file managers, git UIs, AI assistants, system monitors, database clients, API testers — but there is **no unified orchestration layer** to compose them into coherent workspaces.

The current landscape forces painful trade-offs:

- **Fragmentation**: Each tool runs in isolation. Switching contexts means manually arranging windows, losing state, and rebuilding layouts.
- **Modal Lock-in**: Traditional multiplexers (tmux, screen) provide raw pane management but zero semantic understanding of what's running where. You navigate by index, not by meaning. Keybinds require a prefix key (Ctrl-b) that interrupts flow.
- **Ephemeral Workspaces**: Close a tmux session and your carefully arranged environment vanishes. Even session managers only restore the skeleton — not the living state of running processes, scroll positions, and tool contexts.
- **No Intelligence Layer**: AI coding assistants exist as standalone apps with no awareness of your workspace topology, running processes, or development context.
- **Domain Blindness**: A music producer, a DevOps engineer, and a student all need fundamentally different tool arrangements, but terminal multiplexers offer one-size-fits-all pane splitting.
- **Flat Navigation**: Terminal panes are one-dimensional — one tool per pane, period. Want to switch from an editor to a shell in the same space? Kill one, start the other, lose your state. There is no concept of layered tools within a single container.
- **No Unified Command Surface**: Settings live in dotfiles, actions live in shell history, live state lives in htop, scripts live in Makefiles — there is no single place where a developer can see, search, execute, and configure everything about their workspace.

Nexus Shell solves this by introducing a **semantic orchestration layer** between the user and their tools — where workspaces are declarative compositions, navigation is identity-based (by role, not by pane index), state persists through a momentum engine, the Command Graph unifies all actions and configuration in one searchable surface, and AI agents operate as first-class citizens within governed protocols.

## 3. Implementation Analogy / Visual
Think of Nexus Shell as a **conductor for a terminal orchestra**.

In a traditional orchestra, each musician (tool) is world-class on their own instrument. But without a conductor, they're just noise. The conductor doesn't play any instrument — they orchestrate timing, dynamics, and coordination so the ensemble produces something greater than the sum of its parts.

Nexus Shell is that conductor:
- **The score** = compositions (JSON layouts defining which tools play where)
- **The musicians** = your CLI/TUI tools (Neovim, Yazi, lazygit, etc.)
- **The baton signals** = the intent resolution pipeline (translating your gestures into coordinated actions)
- **The conductor's hand gestures** = the modeless keymap (Alt+key — always available, no prefix, no modes, the conductor never stops to change grip)
- **The concert hall** = tmux (the physical stage where performance happens)
- **The rehearsal notes** = momentum engine (remembering how the last performance went, restoring it perfectly)
- **The music stands** = tab stacks (each stand holds multiple scores layered; the musician flips between pieces without leaving their seat)
- **The program booklet** = the Command Graph (the audience's single reference for everything happening, searchable, editable, alive)
- **The guest soloist** = AI agents (joining the ensemble under the conductor's governance)

No conductor tells a violinist HOW to play violin. Similarly, Nexus never wraps or replaces your tools — it orchestrates them.

## 4. Key Values
- **Target Audience**: Power users and developers who live in the terminal: software engineers, DevOps practitioners, data engineers, AI researchers, technical writers, music producers using CLI tools, students, and anyone who wants their terminal to be a sovereign, intelligent workspace rather than a dumb grid of panes.
- **Core Value Prop**: Transform your terminal from a collection of disconnected tools into a sovereign, intelligent, domain-aware workspace that remembers its state, understands your intent, orchestrates your favorite tools into instant compositions, unifies all actions and configuration in a single searchable command graph, and governs AI agents through principled protocols — all without replacing a single tool you already use.

---
**Protocol Note**: The Idea phase is for high-level alignment before Requirements are drafted.
