# Nexus Shell: The Path to Agentic Sovereignty

This roadmap outlines the evolution of Nexus Shell from a terminal multiplexer into a high-performance, sovereign, open-source IDE — a **Meta-IDE** that orchestrates the best open-source tools into a unified development experience.

---

## 🟢 Phase 1–3: Foundations (Baselined)
- [x] **UI & Session Layer**: Guarded session handling, recursive process cleanup, and YAML-driven menus.
- [x] **Engine Layer**:
    - [ ] **LiteLLM AI Proxy Submodule**:
        - Create an optional `litellm` proxy capability that sits between the AI tool (e.g. opencode, cursor) and the API.
        - The proxy mimics the expected API (e.g. OpenAI style) but allows the user to switch models seamlessly via an interactive CLI menu.
        - Keeps `litellm` entirely out of the core dependencies but enables instantaneous model switching without restarting the AI tools.
    - [ ] **Extensibility Model (Python backend)**: Easy addition of tools (e.g., swapping `yazi` for `broot`).
    - [ ] **Modular Configurations**: Per-tool configurations loaded dynamically (e.g., separate Yazi, Tmux, Git configurations in `~/.nexus`).

---

## ✅ Phase 4: Composable Orchestration (The Multi-Root Engine)
- [x] **Multi-Folder Workspaces**: Multiple root directories in a single unified workspace.
- [x] **Project Profiles**: Hot-swappable environment definitions (Theme + Keybinds + Composition).
- [x] **Modular Keybind Profiles**: Live-swappable keyboard layouts (Vim, VSCode, Minimal).
- [x] **Modular HUD Architecture**: Decoupled status rendering per workspace/profile.
- [x] **Ascent (Domain Workspace)**: First specialized environment for learning.

---

## 🛠️ Phase 5: IDE Intelligence (The Desktop Killer)

### Completed
- [x] **Global Jump-to-Definition**: Cross-pane LSP intelligence for instant editor navigation from stack traces.
- [x] **The Merge Conflict Matrix**: Auto-detect conflicts and auto-spawn a dedicated 3-way split review layout.
- [x] **Headless DAP (Debug Adapter Protocol)**: Decoupled debug REPLs for Python and Node.js.

### In Progress
- [ ] **Diagnostics Hub**: Background piping of LSP errors/linting into the Status HUD.
- [ ] **Symbolic Navigation**: Workspace-wide fuzzy symbol search (`Alt-s`).
- [ ] **Local History**: Per-file shadow backups and undo-history ("Time Machine for Code").
- [ ] **Interactive Command Palette**: Unified `Alt-p` entry point for commands, manifests, and buffers.
- [ ] **Master Switcher**: Context-aware `Alt-m` for fuzzy-switching between Nvim tabs, Shell tabs, and Project Slots.

---

## 🏛️ Phase 5.5: Sovereign UX (Modeless Sovereignty)

The "Make It Yours" release. Nexus Shell stops being a multiplexer and becomes a sovereign environment.

### Keybind Architecture (Locked Design)
Two fully separate, non-overlapping layers. All bindings user-configurable via `config/keybinds/`:
- **Layer 1 — Nexus IDE Keys** (`Alt-*`, global, Tmux root table):  
  `Alt-v/s` splits, `Alt-f` focus, `Alt-w` close, `Alt-h/j/k/l` navigate, `Alt-1-9` windows.
- **Layer 2 — Menu Action Keys** (`Ctrl-*`, fzf-internal only, captured by fzf before Tmux sees them):  
  `Enter` execute, `Ctrl-E` edit/configure, `Ctrl-F` favorite/pin, `Ctrl-O` drill-in, `Ctrl-B` back, `Esc` exit.
- `Ctrl-\` = Command palette (`:wq`, `:save <name>`, etc.) — unchanged.

### Interaction Model
- [ ] **Modeless Flat Keymap**: Strip all modal state (Normal Mode). `Alt` (Option) is the universal modifier.
- [ ] **Quantum Splits**: `Alt-v` (vertical), `Alt-s` (horizontal), `Alt-w` (close pane).
- [ ] **Quantum Focus**: `Alt-f` to instantly maximize/restore the current pane.
- [ ] **Action/Modify Duality**: `Enter` executes, `Alt-E` edits/configures — universally, on every item.

### Cascading Discovery (Global → Profile → Project)
- [ ] **3-Tier Intelligence Hierarchy**: The menu scans `$NEXUS_HOME/global/`, then `profiles/<type>/`, then `.nexus/`. Project always wins.
- [ ] **Recursive Folder Discovery**: Subdirectories in `.nexus/notes/research/` appear as drill-down folders.
- [ ] **Refined Taxonomy**: Replace the broad "Actions" bucket with purpose-driven pillars:
    - `build/` — Compilation, tests, CI.
    - `launch/` — Dev servers, LLMs, daemons.
    - `scripts/` — General automation.
    - `vision/` — Mermaid diagrams, architectural visualizations.
    - `agents/` — Prompt templates, AI-specific scripts.
    - `notes/` — Knowledge base, specs, mission logs.
    - `places/` — Bookmarks, project shortcuts.

### Layout Sovereignty
- [ ] **Layout Export**: `:save <name>` to freeze the current live geometry into a reusable `.nexus/compositions/<name>.json`.
- [ ] **Layout Undo**: "I accidentally closed a pane" — restore the previous pane state.
- [ ] **Indestructible Momentum**: Perfect geometry and tool persistence across every restart.

### Visual Sovereignty
- [ ] **Unified Renderer (`nxs-view`)**: Smart dispatcher for high-fidelity terminal visualization:
    - Markdown → `glow` paging.
    - Mermaid → `mmdc` + **Kitty/Ghostty Graphics Protocol** (pixel-perfect diagrams in-pane).
    - Code → Syntax-highlighted source preview (`bat`).
- [ ] **Ghostty Native Rendering**: Leverage Ghostty/Kitty image protocols for rich media within the terminal.

### Workspace Polish
- [ ] **Tab UX**: Tab renaming, reordering, and contextual icons.
- [ ] **Notifications & Toasts**: Ephemeral popup messages for build success/failure, save confirmation, and event bus signals.
- [ ] **Onboarding Overlay**: `Alt-?` to show all active keybindings contextually as a transparent overlay.
- [ ] **Snippet/Template System**: Project scaffolding from the menu (e.g., "New Rust Module", "New Python Package").

---

## 🔌 Phase 5.7: Pane Telemetry (The Nervous System)

The leap from "Manager of Space" to "Manager of Intelligence." Panes stop being silos.

- [ ] **Cross-Pane Event Wiring**: When a build fails in the Terminal pane, the Editor pane jumps to the error line.
- [ ] **Event Bus → HUD Bridge**: The Status HUD reflects real-time state from the Event Bus (Git branch, LSP errors, active profile, server health).
- [ ] **Sovereign Search**: A unified query stream that indexes Notes, Actions, Code, and Vision into one `Alt-F` experience.
- [ ] **Pervasive Context Pumping**: Real-time telemetry streaming (active file, cursor position, build errors) into Context Buckets.

---

## 🧠 Phase 6.5: The AI Control Surface

The leap from "Pane with a chat tool" to a **Sovereign Agent Slot** — one pane, infinite intelligence.

### The Stack
- **LiteLLM proxy** (`localhost:8080/v1`) — Unified model gateway. One endpoint for cloud and local models.
- **`superpowers`** — Skill/hook/command plugins for Claude Code and OpenCode.
- **`agency-agents`** — Library of markdown role definitions (Senior Engineer, DevOps, etc.).
- **`context-mode`** — Claude Code context manager with CLI.
- **`OpenViking`** — High-performance RAG for workspace-wide grounded memory.

### Features
- [ ] **Agent Slot (`@agent` role)**: Every layout has one dedicated `@agent` pane. What runs in it is fully configurable.
- [ ] **`.nexus/agents/default.yaml` Schema**: Declarative config for the agent pane:
    - `backend`: `claude-code` | `pi` | `opencode`
    - `api_base`: `http://localhost:8080/v1` (LiteLLM proxy — routes to any cloud or local model)
    - `model`: any model name in `LiteLLM/litellm_config.yaml` (Claude Sonnet, Gemini Flash, Qwen3-4B, etc.)
    - `role`: Path to a markdown system prompt from `agency-agents/`
    - `context`: `superpowers` | `context-mode` | none
    - `rag`: `openviking` | none
- [ ] **Model Selector**: From `Agents` menu → `Change Model` → fzf list pulled live from `litellm_config.yaml`. Instantly respawns agent with new model.
- [ ] **Role Selector**: From `Agents` menu → `Change Role` → browse `agency-agents/` roles, load as system prompt.
- [ ] **Context-Injected Boot**: On launch, reads agent config, sets `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL`, and spawns backend with correct flags.
- [ ] **Multi-Agent Layouts**: Different windows can run different agent configs (Pi in Window 0, Claude Code + Qwen local in Window 1).

---

## 🚀 Phase 6: AI Sovereignty & Multimodal Creative Labs

### Completed
- [x] **Daemon Manager**: Invisible background orchestration for LSPs, DAPs, and AI backends.
- [x] **Pi Frontend Integration**: Lightweight, conversational TUI bridge to background agent engines.

### In Progress
- [/] **Agent Follow Mode ("Ghost Driving")**: Real-time editor/shell orchestration where the agent physically demonstrates changes.

### Planned
- [ ] **Agnostic AI Interface**: Unified Context Bridge for Claude Code, Pi, and OpenCode — one `@agent` slot, many backends.
- [ ] **Context Database Integration**: High-performance RAG via **OpenViking** for workspace-wide memory.
- [ ] **SystemPrompt OS (Identity)**: Native enforcement of "Separation of Powers" and "Context Buckets" from the `@agents` project.
- [ ] **Music/DSP Module**: Specialized workspace for code-driven music composition (FluidSynth/SuperCollider integration).
- [ ] **Agent Zero: Headless Migration**: Complete decoupling of the reasoning engine from the Gradio UI.

---

## 🛡️ Phase 7: Sovereign Management (GAP)

GAP is the **specification and governance engine** for autonomous agent work. It is NOT embedded in Nexus Shell — it is an external protocol that agents operate inside.

### The Two Modes
- **Normal Claude / Pi**: Unchanged. You chat, you code, no restrictions. GAP doesn't exist in this mode.
- **GAP Session** (`gap claude`): Opens an agent in *alignment mode*. The agent and supervisor collaboratively write specs (Requirements → Design → Tasks → Plan). Nothing executes until the Plan is locked.

### The Two Phases
1. **Alignment Phase** — Agent + Supervisor write specs together. GAP provides a `.claude-plugin` / skill so the agent knows the GAP workflow. Output: approved Plan with execution envelopes (model, locality, checkpoints).
2. **Autonomous Execution** — `gap execute`: deterministic CLI that dispatches the approved Plan to a sandboxed VM (OrbStack/Docker). Agent works on an isolated Git worktree. Results return as PR/diff.

### Nexus Shell's Role (Minimal)
- [ ] **Boot Surface**: Launch `gap claude` in the agent pane (via `gap_session: true` in `.nexus/agents/`)
- [ ] **Gate Approval UI**: fzf-based `gap gate list` → approve/reject from the menu
- [ ] **Execution Dispatch**: Trigger `gap execute` from the menu when the Plan is approved
- [ ] **Archive Dead GAP Code**: Remove `gap_bridge.sh`, `gap_service.sh`, `gap_runner.sh`, `nxs-pi-gap.sh`

### GAP Project Tasks (External)
- [ ] **`.claude-plugin` for GAP alignment mode** — skill/hook that teaches the agent the GAP workflow
- [ ] **`gap claude` CLI wrapper** — context injection + alignment session boot
- [ ] **`gap execute` CLI** — deterministic dispatch to sandboxed VM with Plan constraints
- [/] **The GAP Engine** — Core CLI (`gap check`, `gap gate`, `gap scribe`) already exists
- [x] **GAP Spec Manager** — TUI for editing alignment artifacts


---

## 🌍 Phase 8: Domain Sovereignty (Profiles & Contexts)

Purpose-built environments that transform Nexus Shell based on context.

- [ ] **School Profile**: Academic/AI research workflow (`config/profiles/school.yaml` + `compositions/school.json`).
- [ ] **Context-Aware Boot**: Nexus detects the project type on launch and auto-suggests the best profile.
- [ ] **Profile Marketplace**: Share and discover community profiles (Rust Developer, Data Science, DevOps, Writer).

---

*Last Updated: 2026-03-14*
