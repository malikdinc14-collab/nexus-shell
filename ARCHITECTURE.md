# Nexus Shell — Architecture & Mission Specs

## Mission

Nexus Shell is a **workspace operating system**. It orchestrates tools, layouts, and workflows into persistent, domain-aware workspaces — for any discipline, on any surface.

The system doesn't replace your tools. It doesn't own your display. It provides the **intelligent wiring** between what you do (capabilities), where you see it (surfaces), and why you're working (packs).

## The Core Principle

**Three extension points. Zero coupling.**

Every feature in Nexus Shell exists as one of three plugin types:

```
┌─────────────────────────────────────────────────────────────┐
│                      nexus-core                             │
│                                                             │
│  Pure Python. No UI. No subprocess. No tmux.                │
│  State management, event bus, configuration, orchestration. │
│                                                             │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ Surfaces │  │ Capabilities │  │ Packs              │    │
│  │          │  │              │  │                    │    │
│  │ WHERE    │  │ WHAT tools   │  │ WHY you're working │    │
│  │ you see  │  │ are available│  │ (domain context)   │    │
│  │ things   │  │              │  │                    │    │
│  └──────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

The architecture is correct when:

- You can run nexus-core with NO tmux installed (pure Python, no subprocess)
- You can add a new tool by writing ONE adapter file (implement the ABC)
- You can add a new display layer by writing ONE surface module (implement Surface)
- You can create a finance workspace by writing ONE YAML pack definition
- You can test everything without a terminal (MockSurface)

## Extension Point 1: Surfaces

A **Surface** is anything that can display and control workspaces — a terminal multiplexer, a tiling window manager, a desktop app, a web browser.

```python
class Surface(ABC):
    """Anything that can host workspaces."""

    # Spatial — create/destroy/focus/resize containers
    def create_container(self, id, layout) -> str: ...
    def destroy_container(self, handle) -> None: ...
    def focus(self, handle) -> None: ...
    def resize(self, handle, dimensions) -> None: ...

    # Content — attach processes to containers
    def attach_process(self, container, command) -> str: ...
    def send_input(self, handle, keys) -> None: ...

    # State — query what exists
    def list_containers(self) -> List[ContainerInfo]: ...
    def get_dimensions(self, handle) -> Dimensions: ...

    # Metadata — tag containers with arbitrary data
    def set_tag(self, handle, key, value) -> None: ...
    def get_tag(self, handle, key) -> str: ...

    # Rendering — display menus, HUD, notifications
    def show_menu(self, items) -> Optional[str]: ...
    def show_hud(self, modules) -> None: ...
    def notify(self, message, level) -> None: ...
```

### Surface implementations

| Surface | Display | Menu renderer | HUD | Status |
|---------|---------|--------------|-----|--------|
| `TmuxSurface` | tmux panes | fzf / gum / Textual | tmux status bar | Current |
| `SwaysSurface` | Sway/i3 containers | rofi / wofi | waybar / eww | Planned |
| `HyprlandSurface` | Hyprland windows | rofi / wofi | waybar / eww | Planned |
| `TauriSurface` | Tauri/WebView | Native UI (React/Svelte) | In-app panel | Planned |
| `WebSurface` | Browser via WebSocket | Web UI | Web dashboard | Planned |
| `CompositeSurface` | WM windows + tmux stacks | Delegated | Both | Planned |

The `CompositeSurface` is the powerful one: a tiling WM manages window placement, tmux manages tab stacks within each window, Nexus orchestrates both through one API. This is the ideal Linux desktop experience.

## Extension Point 2: Capabilities

A **Capability** is an abstract interface for a category of tool. An **Adapter** is a concrete implementation.

```python
class Capability(ABC):
    manifest: AdapterManifest  # name, priority, binary, availability
    def is_available(self) -> bool: ...

class EditorCapability(Capability):
    def open_resource(self, path, line, col) -> bool: ...
    def get_current_buffer(self) -> Optional[str]: ...
    def apply_edit(self, patch) -> bool: ...

class ExplorerCapability(Capability):
    def list_directory(self, path) -> List[dict]: ...
    def get_selection(self) -> Optional[str]: ...

class ExecutorCapability(Capability):
    def spawn(self, command, cwd, env) -> str: ...
    def kill(self, handle) -> bool: ...

class MenuCapability(Capability):
    def show_menu(self, options, prompt) -> Optional[str]: ...

class MultiplexerCapability(Capability):   # Legacy — merging into Surface
    def create_session(self, name) -> str: ...
    def split(self, target, direction) -> str: ...
    ...
```

### Current adapters

| Capability | Adapters | Adding a new one |
|-----------|----------|-----------------|
| Editor | Neovim, (Helix, Micro planned) | Implement `EditorCapability` ABC |
| Explorer | Yazi | Implement `ExplorerCapability` ABC |
| Agent | OpenCode | Implement `ChatCapability` ABC |
| Menu | fzf, gum, Textual, null (fallback) | Implement `MenuCapability` ABC |
| Multiplexer | tmux, null (fallback) | Implement `MultiplexerCapability` ABC |

### Adding a capability for a new domain

For music production, you might add:

```python
class AudioMonitorCapability(Capability):
    def get_levels(self) -> Dict[str, float]: ...
    def get_bpm(self) -> int: ...
    def is_playing(self) -> bool: ...

class ReaperAdapter(AudioMonitorCapability):
    manifest = AdapterManifest(name="reaper", binary="reaper", ...)
    ...
```

The registry auto-discovers adapters. The pack references the capability. The surface renders it.

## Extension Point 3: Packs

A **Pack** is a domain module — it answers "what does this project/workflow need?"

```yaml
# packs/music-production.yaml
name: music-production
description: DAW-centric workspace for music creation
version: "1.0"
markers: ["*.als", "*.flp", "*.rpp", "Ableton*", "*.wav"]

capabilities:
  editor: reaper          # preferred adapter for this domain
  explorer: yazi
  monitor: audio-levels   # domain-specific capability

compositions:
  - name: studio
    description: "DAW left, mixer right, terminal bottom"
    layout:
      type: hsplit
      children:
        - { weight: 60, capability: editor }
        - type: vsplit
          children:
            - { weight: 50, capability: monitor }
            - { weight: 50, capability: executor }

hud_modules:
  - bpm_display
  - audio_levels
  - midi_activity
  - cpu_load

commands:
  - id: render-mp3
    label: "Render to MP3"
    type: action
    command: "reaper -renderproject"
  - id: open-audacity
    label: "Edit in Audacity"
    type: action
    command: "audacity ${selected_file}"

connectors:
  - trigger: "filesystem.change:*.wav"
    action: "notify:New audio file detected"
  - trigger: "editor.save"
    action: "shell:auto-bounce.sh"

keybinds:
  Alt+r: render-mp3
  Alt+b: toggle-bpm-display
```

### Pack examples across domains

| Domain | Pack | Key capabilities | HUD modules |
|--------|------|-----------------|-------------|
| **Music Production** | `music-production` | Reaper/Ableton, audio monitor, MIDI | BPM, levels, MIDI activity |
| **Writing** | `writing` | Neovim (prose mode), word count, Pandoc | Word count, chapter progress, export status |
| **Finance** | `finance-tracking` | Spreadsheet viewer, chart renderer | Portfolio value, P&L, market status |
| **AI Art** | `ai-image` | ComfyUI, image viewer, prompt editor | GPU usage, queue depth, generation progress |
| **Video Production** | `video-editing` | DaVinci Resolve, ffmpeg, preview | Timeline position, render progress, disk space |
| **Coding (Rust)** | `rust-dev` | Neovim, cargo, bacon (test watcher) | Build status, test results, clippy warnings |
| **Learning** | `study` | PDF viewer, note-taking, flashcards | Session timer, cards due, progress |
| **DevOps** | `devops` | k9s, lazydocker, SSH | Cluster health, pod status, alerts |

## Profiles

A **Profile** answers "how do I like to work?" — orthogonal to packs.

Same pack + different profile = same tools, different layout and theme.

```yaml
# profiles/focused.yaml
name: focused
description: "Minimal distractions, single-pane dominant"
composition: minimal
theme: catppuccin-mocha
hud: [clock, git_branch]
keybinds: {}

# profiles/dashboard.yaml
name: dashboard
description: "Everything visible, multi-pane monitoring"
composition: quad
theme: nexus-cyber
hud: [clock, git_branch, cpu, memory, ports, processes]
```

## Core Modules

The core has no dependencies on any surface or specific tool. It is a pure Python library.

```
nexus-core/
├── models.py        — Tab, TabStack, Pane, Workspace, Composition (dataclasses)
├── state.py         — WorkspaceState: the single source of truth
├── capabilities.py  — ABC definitions + AdapterManifest + Registry
├── surfaces.py      — Surface ABC
├── packs.py         — Pack loader, detector, lifecycle
├── profiles.py      — Profile loader, active switching
├── config.py        — CascadeResolver (workspace > profile > global)
├── bus.py           — Event pub/sub with typed events
├── graph.py         — Command graph nodes, loader, resolver, live sources
├── momentum.py      — Session save/restore, proportional geometry
├── connectors.py    — Event-to-action automation
└── api.py           — NexusCore facade (the single entry point)
```

### NexusCore API (the facade)

```python
class NexusCore:
    """Single entry point for all nexus operations."""

    def __init__(self, surface: Surface, config_dir: str): ...

    # Workspace
    def create_workspace(self, name, pack=None, profile=None) -> Workspace: ...
    def save_workspace(self) -> None: ...
    def restore_workspace(self, name) -> None: ...
    def switch_composition(self, name) -> None: ...

    # Tab Stacks
    def push_tab(self, pane_id, capability_type, adapter=None) -> Tab: ...
    def pop_tab(self, pane_id) -> Optional[Tab]: ...
    def rotate_tabs(self, pane_id, direction) -> Optional[Tab]: ...

    # Command Graph
    def open_menu(self) -> List[MenuItem]: ...
    def select_menu_item(self, node_id, mode="new_tab") -> Action: ...
    def resolve_live_sources(self) -> Dict[str, str]: ...

    # Packs & Profiles
    def suggest_packs(self, directory) -> List[Pack]: ...
    def enable_pack(self, name) -> bool: ...
    def switch_profile(self, name) -> bool: ...

    # Events
    def publish(self, event_type, data) -> None: ...
    def subscribe(self, pattern, callback) -> None: ...

    # Config
    def get_config(self, key) -> Any: ...
    def reload_config(self) -> None: ...
```

Every CLI command, every keybinding, every UI interaction calls through this API. The surface is injected at construction. Nothing in the core knows which surface is active.

## Current State (honest)

### What works
- Capability adapter framework with registry and auto-discovery
- Tab stack data model, manager, persistence, and proportional geometry restore
- Config cascade (workspace > profile > global)
- Command graph with node types, YAML loading, scope resolution, live sources
- Event bus with typed events, wildcards, dead subscriber detection
- Pack detection and suggestion; profile switching
- CLI with full subcommand dispatch
- 738 passing tests
- tmux boot, keybindings, compositions (23 layouts)

### What needs work
- **Surface abstraction doesn't exist yet** — MultiplexerCapability is close but needs generalization
- **Shell/Python duplication** — 44 kernel shell scripts, 15 of which are dead code. Live ones duplicate Python engine logic.
- **Two CLI implementations** — legacy intent resolver and new subcommand dispatch. Need unification.
- **No logging** — errors silently swallowed throughout
- **Packs are thin** — detect markers and list tools, but don't define compositions, HUD, commands, or connectors yet
- **End-to-end flow untested** — modules work in isolation, full keybind-to-display chain not verified

### Migration path
1. Delete 15 dead shell scripts in `kernel/exec/`
2. Extract Surface ABC from MultiplexerCapability
3. Create TmuxSurface by pulling tmux-specific code out of handlers
4. Create NexusCore facade wrapping existing modules
5. Enrich Pack dataclass with compositions, HUD, commands, connectors
6. Migrate kernel shell scripts to thin wrappers around `nexus-ctl`
7. Build second surface (Sway or Tauri) to prove the abstraction

## Navigation Model

Modeless. Alt (Option) is the universal modifier. No prefix keys. No modes.

| Key | Action | Scope |
|-----|--------|-------|
| `Alt+h/j/k/l` | Move focus between containers | Spatial |
| `Alt+m` | Open Command Graph menu | Global |
| `Alt+o` | Open capability launcher | Global |
| `Alt+t` | Tab manager (list/jump) | Per-container |
| `Alt+n` | Push new tab | Per-container |
| `Alt+w` | Pop active tab (warns on last) | Per-container |
| `Alt+q` | Kill container + all tabs | Per-container |
| `Alt+[` / `Alt+]` | Rotate tabs left/right | Per-container |
| `Alt+v` / `Alt+s` | Split vertical/horizontal | Spatial |
| `Enter` | Open selection as new tab | Convention |
| `Shift+Enter` | Replace current tab with selection | Convention |

This keymap is surface-independent — Alt+h means "focus left" whether that's a tmux pane, an i3 container, or a Tauri panel.

## Event Bus & Connectors

The event bus is the inter-tool nervous system. Connectors are automation rules.

```yaml
# .nexus/connectors/auto-test.yaml
connectors:
  - name: test-on-save
    trigger: "editor.save:*.py"
    action: "shell:pytest --tb=short"

  - name: refresh-on-git
    trigger: "filesystem.change:.git/HEAD"
    action: "internal:refresh_live_sources"
```

Event types: `filesystem.*`, `editor.*`, `test.*`, `ai.*`, `ui.*`, `system.*`

## Design Principles

1. **Bring Your Own Tools** — Nexus orchestrates; it never replaces. Your editor, your explorer, your shell.
2. **Sovereign by default** — The user approves. AI agents propose; humans execute. No silent automation.
3. **Surface-agnostic** — The core doesn't know if it's rendering in tmux, a browser, or a desktop app.
4. **Pack-driven domains** — Any workflow becomes a pack. Music, finance, writing, coding — same system, different packs.
5. **State belongs to the core** — Surfaces are dumb renderers. The Python core is the single source of truth.
6. **Fail visible** — No silent swallowing. Errors surface. Fallbacks are explicit (null adapters, not empty strings).
7. **Convention over configuration** — Sensible defaults, override anything. Cascade: workspace > profile > global.
8. **Indestructible workspaces** — Save on exit, restore on boot. Proportional geometry adapts to any screen.

## License

MIT
