# Nexus Shell

**A workspace operating system.** Orchestrates tools, layouts, and workflows into persistent, domain-aware workspaces — for any discipline, on any surface.

Nexus Shell doesn't replace your tools. It doesn't own your display. It provides the intelligent wiring between **what you do** (capabilities), **where you see it** (surfaces), and **why you're working** (packs).

## The Idea

Your terminal has incredible tools — Neovim, Yazi, fzf, lazygit, btop, and hundreds more. But they don't talk to each other. They don't remember where you left off. They can't adapt to whether you're writing code, producing music, or tracking expenses.

Nexus Shell is the orchestration layer that connects them.

```
┌──────────────────────────────────────────────┐
│               nexus-core (Python)             │
│   State, events, config, orchestration.       │
│   No UI dependencies. No tmux. No shell.      │
│                                               │
│   Surfaces      Capabilities      Packs       │
│   (WHERE)       (WHAT tools)      (WHY)       │
│                                               │
│   tmux          Neovim            coding      │
│   i3/Sway       Yazi              music       │
│   Tauri         fzf               writing     │
│   Web           OpenCode          finance     │
│   Hyprland      Reaper            ai-art      │
│   ...           ...               ...         │
└──────────────────────────────────────────────┘
```

- **Surface**: anything that displays workspaces — tmux, a tiling WM, a Tauri app, a browser
- **Capability**: an abstract tool interface — editor, explorer, agent, menu, audio monitor
- **Pack**: a domain module — what tools, layouts, HUD modules, and automations a workflow needs

## Quick Start

```bash
git clone https://github.com/samir-alsayad/nexus-shell.git
cd nexus-shell
./bin/nxs
```

Currently runs on **tmux** (macOS/Linux). Future surfaces: Sway, Hyprland, Tauri, Web.

## Navigation

Modeless. `Alt` is the universal modifier. No prefix keys. No modes.

| Key | Action |
|-----|--------|
| `Alt+h/j/k/l` | Move focus between panes |
| `Alt+m` | Open Command Graph (menu) |
| `Alt+o` | Open capability launcher |
| `Alt+n` | Push new tab onto stack |
| `Alt+w` | Pop active tab |
| `Alt+[` / `Alt+]` | Rotate through tabs |
| `Alt+v` / `Alt+s` | Split vertical / horizontal |
| `Alt+q` | Kill pane |

`Enter` opens as new tab. `Shift+Enter` replaces current tab.

## Key Concepts

### Tab Stacks

Every pane holds a **stack of tabs** — multiple tools layered on top of each other. Push a terminal on top of your editor, rotate back, push a chat agent. Inactive tabs live in a background reservoir. Workspaces persist across reboots with proportional geometry that adapts to any screen size.

### Command Graph

A unified command surface — not a simple menu. Every action, setting, live data source, and navigation target is a node in a scoped, searchable tree. Nodes resolve through a three-tier cascade: workspace > profile > global.

### Packs

Domain modules that define what a workflow needs:

| Pack | Tools | HUD | Automations |
|------|-------|-----|-------------|
| `rust-dev` | Neovim, cargo, bacon | Build status, test results | Save triggers test run |
| `music-production` | Reaper, audio monitor | BPM, levels, MIDI | File change triggers notify |
| `writing` | Neovim (prose), Pandoc | Word count, chapter progress | Save triggers export |
| `finance` | Spreadsheet, chart viewer | Portfolio, P&L | Import triggers categorize |
| `ai-art` | ComfyUI, image viewer | GPU, queue depth | Generation triggers preview |

### Profiles

Orthogonal to packs. Same tools, different arrangement:

- **focused** — single dominant pane, minimal HUD
- **dashboard** — quad layout, everything visible
- **presentation** — clean, large fonts, status hidden

## Architecture

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the full mission specs, Surface/Capability/Pack ABCs, core module map, migration plan, and design principles.

## Current Status

**Core (complete):**
- Surface ABC — pluggable display layer with NullSurface fallback
- NexusCore facade — single entry point, Surface injected at construction
- Capability adapter framework (Neovim, Yazi, fzf, gum, Textual, OpenCode, tmux)
- Tab stacks with push/pop/rotate and session persistence
- Command Graph with 3-layer cascade (workspace > profile > global)
- Live source resolvers (git, tmux, processes, ports)
- Config cascade, event bus with typed events, pack detection
- Pack dataclass with compositions, HUD, commands, connectors, keybinds
- Unified CLI (`nexus-ctl`) with legacy compatibility
- 692 passing tests

**tmux surface (working):**
- 23 compositions (layouts)
- Modeless Alt+ keybindings
- Workspace persistence with proportional geometry
- Menu popup via fzf/gum with live source data

**Roadmap:**
- Domain packs (rust-dev, python-dev, writing, music, finance)
- HUD module framework (pack-driven status bar widgets)
- Textual Surface (Python TUI — headless testing, no tmux required)
- Sway/i3 Surface via i3ipc-python
- CompositeSurface (tiling WM + tmux tab stacks)
- Connector system (event-to-action automation)

## Requirements

- Python 3.10+
- tmux 3.3+
- One of: fzf, gum, or python-textual (for menu rendering)
- Recommended: Neovim, Yazi, lazygit

## License

MIT
