# Nexus Shell — Architecture Theory

This document captures the design theory behind Nexus Shell's extension and distribution model. It complements `design.md` (data models, interface contracts) and `ARCHITECTURE.md` (mission specs, ABCs, module map).

---

## 1. The Three-Layer Model

Nexus Shell's architecture separates into three distinct layers, analogous to the Linux ecosystem:

```
+-------------------------------------------------------+
|  EXTENSIONS                                           |
|  User/community-authored. Portable across surfaces.   |
|  Actions, Menu Trees, Packs, Modules, Themes          |
+-------------------------------------------------------+
|  ENGINE                                               |
|  Capability ABCs, Adapter Registry, Event Bus,        |
|  State, Command Graph, Scope Cascade                  |
+----------+-----------+-----------+--------------------+
|  tmux    |  Tauri    |  Web App  |  Sway / i3 / etc.  |
|  surface |  surface  |  surface  |  surface            |
+----------+-----------+-----------+--------------------+
```

| Linux Equivalent    | Nexus Equivalent                        | Role                                                  |
|---------------------|-----------------------------------------|-------------------------------------------------------|
| Kernel + syscalls   | Engine + Capability ABCs                | Abstract interface. Extensions call this, never below. |
| Desktop environment | Surface / Distribution (tmux, Tauri, Web) | Rendering + input. Implements the ABCs.              |
| Packages            | Extensions (packs, actions, menu trees) | Portable units that declare needs, not implementations.|
| Package manager     | Registry + Loader                       | Discovery, installation, dependency resolution.       |
| Drivers             | Adapters                                | Surface-specific implementations of abstract interfaces.|

### The Critical Invariant

> **Extensions (user-authored artifacts) never import or reference anything below the Engine layer.**

A pack that declares `command: "pytest"` works on tmux, Tauri, web, and Android because the engine decides HOW to run that command on each surface. A pack that calls `subprocess.run(["tmux", "split-window"])` is broken.

This is the same guarantee Linux provides: a well-behaved program calls `open()` / `write()` / `fork()` and doesn't talk to the disk controller. That's what makes it portable across hardware.

---

## 2. Extension Hierarchy

Extensions range from trivial to complex. Each level has a clear author, packaging model, and portability guarantee.

### Level 1 — Action (simplest)

A single script with a metadata header. Like a shell alias with structure.

```bash
#!/bin/bash
# @nexus-action
# @name: Deploy Staging
# @id: project:deploy-staging
# @icon: rocket

./scripts/deploy.sh staging
```

The user writes the script. The engine discovers it by convention (from `.nexus/actions/` or `~/.config/nexus/actions/`), shows it in the Command Graph, and dispatches it through adapters when selected. On tmux, it spawns in a pane. On Tauri, it opens a terminal panel. On web, it streams output to a panel.

### Level 2 — Menu Tree (pure data)

A YAML file declaring Command Graph nodes. Zero code. Pure structure.

```yaml
# .nexus/menus/my-tools.yaml
nodes:
  - id: custom.docker-logs
    label: "Docker Logs"
    type: action
    command: "docker compose logs -f"
    icon: whale
    tags: [docker, logs]
```

Drops into `~/.config/nexus/menus/` (global) or `.nexus/menus/` (workspace). Merges into the Command Graph via the scope cascade. Works on every surface without modification.

### Level 3 — Pack (domain bundle)

A `pack.yaml` manifest declaring markers, tools, connectors, menu nodes, and services. Like a "language support extension" in VS Code.

```yaml
name: python-dev
markers: [pyproject.toml, setup.py, requirements.txt]
capabilities:
  executor: ipython
menu_nodes:
  - id: pack.python.test
    label: "Run Tests"
    command: "pytest --tb=short"
connectors:
  - trigger: "editor.save:*.py"
    action: "shell:pytest --tb=short -q"
```

Community-shareable. The pack never says HOW — it says WHAT. "I need an executor, I provide these menu nodes, wire these events." The engine and surface handle execution.

### Level 4 — Module (adapter / bridge)

Implements a Capability ABC. Written by tool authors, not end users.

Examples: a Helix editor adapter, a Zellij multiplexer adapter, a Wezterm surface module. These are the "drivers" of the system.

Each module has a `module.yaml` manifest:

```yaml
name: helix-adapter
type: adapter
capability: editor
binary: hx
priority: 90
```

Community-shareable: `nexus module install helix-adapter`. But fundamentally different from Levels 1-3 — modules contain Python code that implements ABCs.

### Level 5 — Surface / Distribution

A complete implementation of the display layer. Like a Linux desktop environment. Written by distribution authors.

A surface implements `MultiplexerCapability` (or the future `Surface` ABC) and provides the rendering pipeline: how panes are drawn, how menus appear, how the HUD renders, how processes are hosted.

Examples: "Nexus for tmux" (current), "Nexus for Tauri", "Nexus for Web", "Nexus for Sway".

Each distribution ships with its own default Level 4 modules (adapters tuned for that surface) but uses the same engine, same packs, same user extensions.

---

## 3. The Hybrid Surface Model

A Tauri or Electron surface doesn't replace nvim with a native text editor. It **wraps** nvim — spawns it as a child process, renders its output through an embedded terminal emulator widget, and the EditorCapability adapter still talks to nvim over the same RPC socket.

This is how Neovide works (wraps nvim in a GPU-rendered GUI), how VS Code embeds terminals (xterm.js), how JetBrains embeds shell processes.

```
+-------------------------------------------------------+
|  SURFACE = Geometry Manager + Process Host            |
|                                                       |
|  +-------------+  +-------------+  +--------------+  |
|  |  Panel A    |  |  Panel B    |  |  Panel C     |  |
|  |  +-------+  |  |  +-------+  |  |  +--------+  |  |
|  |  | nvim  |  |  |  | yazi  |  |  |  | zsh    |  |  |
|  |  | (PTY) |  |  |  | (PTY) |  |  |  | (PTY)  |  |  |
|  |  +-------+  |  |  +-------+  |  |  +--------+  |  |
|  +-------------+  +-------------+  +--------------+  |
|                                                       |
|  MultiplexerCapability = manages the panels           |
|  Terminal emulator      = renders the PTYs            |
|  The tools themselves   = unchanged, same processes   |
+-------------------------------------------------------+
```

### What Changes Per Surface

| Component                | tmux                     | Tauri                          | Web                          |
|--------------------------|--------------------------|--------------------------------|------------------------------|
| **Geometry management**  | tmux panes & windows     | Native panels (CSS grid/flex)  | DOM panels (flexbox)         |
| **Process hosting**      | tmux PTY (built-in)      | Embedded terminal (alacritty-core) | WebSocket to server-side PTY |
| **Tool rendering**       | tmux renders the PTY     | Terminal widget renders PTY    | xterm.js via WebSocket       |
| **EditorCapability**     | NeovimAdapter (unchanged)| NeovimAdapter (unchanged)      | NeovimAdapter (unchanged)    |
| **Menu rendering**       | fzf-tmux popup           | Native command palette         | React component              |
| **HUD**                  | tmux status-line         | Native title bar + status      | DOM header                   |

The tools (nvim, yazi, zsh) are the same processes everywhere. The surface decides how to host and render them. The adapter contracts don't change.

### Native Widgets vs Embedded Terminals

On a native surface (Tauri, Electron), each capability slot offers a choice:

- **Wrap the CLI tool** — embed nvim in a terminal widget. Full feature parity. User keeps their config.
- **Go native** — build a native editor panel (Monaco, CodeMirror). Better integration, but loses the tool's ecosystem.

The user controls this via `adapters.yaml`:

```yaml
# Wrapped CLI tool (default, recommended)
editor: neovim       # NeovimAdapter -> nvim via RPC, rendered in terminal widget

# Native panel (optional, per-surface)
editor: tauri-editor  # TauriEditorAdapter -> Monaco/CodeMirror in native panel
```

Same capability contract. Different adapter. User's choice. The system supports both without architectural changes.

The recommended approach is to **wrap CLI tools first** — don't build native GUI replacements for tools like nvim, yazi, lazygit, etc. Embedding them in terminal widgets gives full compatibility immediately. Native panels can be added incrementally for specific use cases.

---

## 4. Content Provider Boundary

Extensions provide data. The engine provides execution. The boundary is defined by a protocol contract.

### What Users Author

| Artifact           | Format                  | Purpose                                         |
|--------------------|-------------------------|--------------------------------------------------|
| Action scripts     | Shell script + header   | Commands to run (build, deploy, test)            |
| Menu trees         | YAML                    | Static Command Graph entries                     |
| Content providers  | Shell script -> stdout  | Dynamic menu content (sessions, branches, files) |
| Boot lists         | YAML                    | Project startup sequences                        |
| Pack manifests     | YAML                    | Domain capability bundles                        |

### The Protocol

Content providers (dynamic list scripts) emit JSON lines to stdout:

```json
{"label": "main (3 ahead)", "type": "ACTION", "payload": "git checkout main", "icon": "git-branch"}
{"label": "feature/auth", "type": "ACTION", "payload": "git checkout feature/auth", "icon": "git-branch"}
```

The engine runs the script, collects JSON lines, merges with static YAML nodes, applies the scope cascade, and passes the merged tree to the menu adapter for rendering.

### YAML for Declarations, Shell for Discovery

Most menu entries are static declarations — "Run Tests", "Open Config", "Deploy Staging". These should be YAML because:

- YAML is parseable without execution (safer, faster, introspectable)
- YAML works on every surface — a native app reads YAML natively
- The Command Graph loader can validate, lint, and merge YAML trees statically

Shell scripts (`list.sh`) exist for one reason: **runtime discovery**. Sessions list, active stacks, git branches — things that don't exist until you ask.

> **Rule: YAML for what you know. Shell for what you discover. Never shell for static content.**

### Live Sources (Python Only)

Live sources are real-time data feeds that update while the menu is open. They query adapter state (active tabs, running processes, git status). These are:

- Python modules, not shell scripts
- System-provided or pack-provided, not user-authored
- Adapter-aware — they call through capability interfaces

If a user wants "show me my docker containers" in the menu, they write a `list.sh` content provider, not a live source. The distinction:

> **Content provider** = runs once when menu opens, emits a static list.
> **Live source** = stays connected, updates in real-time, queries adapter state.

### Boot Lists

Boot lists are YAML declarations with engine orchestration:

```yaml
# .nexus/boot.yaml
boot:
  - name: "Start API server"
    command: "npm run dev"
    role: terminal
    wait_for: "ready"        # wait for stdout pattern before next step

  - name: "Open main file"
    command: "src/index.ts"
    role: editor
```

The user writes the YAML and the commands. The engine reads it and dispatches through adapters — `mux.send_command()` for terminal roles, `editor.open_resource()` for editor roles. Same boot.yaml works on every surface.

---

## 5. Renderer Capability (General-Purpose Viewports)

Panes are not limited to terminal content. A pane is a general-purpose viewport that can host any content type through the `RendererCapability` interface.

### The Concept

A tab stack can mix content types: a terminal tab running nvim, a markdown preview tab, a web browser tab, a PDF viewer tab — all in the same pane, rotated with Alt+[/].

The `RendererCapability` defines a uniform interface for rendering any content type:

- `render(content_type, source)` → viewport handle
- `is_interactive()` → whether the viewport accepts input (clicks, scrolling)
- `send_input(handle, event)` → forward user interaction to the renderer
- `get_state(handle)` → query renderer state (scroll position, selection, etc.)

### Content Type Adapters

Each content type has adapters that degrade gracefully across surfaces:

| Content Type | tmux (terminal) | Web / Tauri (native) |
|-------------|-----------------|----------------------|
| Terminal | tmux pane (default) | xterm.js widget |
| Markdown | `glow` or `bat` in terminal | HTML render in panel |
| Web page | `w3m` / `lynx` | iframe / WebView |
| PDF | `termpdf` / text fallback | PDF.js / native viewer |
| Image | `chafa` / `sixel` | `<img>` tag |
| 3D viewport | N/A (future) | WebGL / embedded viewer |

### Why This Matters

On tmux, every renderer degrades to a terminal tool. The system works, but everything is text.

On Tauri, renderers get native panels. This is what makes a native app compelling — not "tmux in a window" but a workspace where one pane runs nvim, another shows a live markdown preview, another has a web browser, another streams a build dashboard. The same workspace definition, dramatically different fidelity.

### Interactive Renderers

Some renderers are interactive — a web page accepts clicks, a PDF viewer accepts scrolling, a 3D viewport accepts rotation. The `RendererCapability` contract supports this: the surface captures input events and forwards them to the renderer adapter, which translates them to the appropriate action.

On tmux, interactivity is limited to what the terminal tool supports. On web/Tauri, it's native browser-level interaction.

---

## 6. Portability Guarantee

The entire extension model is designed around one guarantee:

> **Everything above the engine is portable. Everything below the engine is surface-specific. The engine is the boundary.**

### Portability Tiers

Not everything is equally portable. Three tiers:

**Data-portable** (guaranteed everywhere):
- YAML menu trees, pack manifests, config files, boot list declarations
- These are pure data — any surface can parse them
- A menu tree written for tmux renders identically on Tauri, web, Sway

**Execution-portable** (Unix surfaces + server-backed web):
- Shell commands, action scripts, content providers
- These run wherever there's a shell — tmux, Tauri (local), Sway, web (server-side)
- Do NOT run client-side in a browser or on mobile without a server

**Behavior-portable** (best-effort, not guaranteed):
- UX semantics: timing, interaction model, rendering fidelity
- A markdown preview in `glow` (tmux) looks different from HTML render (Tauri)
- Alt+m opens a menu everywhere, but the menu UX differs per surface
- Same workspace, different experience — acceptable and expected

### The Guarantee

- A pack written for the tmux distribution works on Tauri without modification.
- An action script written on macOS works on Linux, web (server-side), Sway.
- A user's menu customizations, profiles, and boot lists carry across surfaces.
- Only adapters (Level 4) and surfaces (Level 5) need per-surface implementations.
- Renderer fidelity improves on richer surfaces, degrades gracefully on terminals.

The user's investment in configuring their workspace is never lost when the surface changes.

---

## 7. Related Specs

- `design.md` — Data models (CommandGraphNode, TabStack, Pack, Profile), interface contracts (keybindings, CLI, event bus, MCP), configuration architecture
- `features/menuv2/implementation_plan.md` — Menu pillars, cascading data sources, resolution policies
- `features/boot-lists/proposals/idea.md` — Boot list design and `.nexus/boot.yaml` format
- `features/module-system/proposals/idea.md` — Module manifest standard, install UX
- `../ARCHITECTURE.md` — Mission specs, Surface/Capability/Pack ABCs, core module map
