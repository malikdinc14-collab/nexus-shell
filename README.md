# Nexus Shell

**A workspace operating system.** Orchestrates tools, layouts, and workflows into persistent, domain-aware workspaces — for any discipline, on any surface.

Nexus Shell doesn't replace your tools. It provides the intelligent wiring between **what you do** (capabilities), **where you see it** (surfaces), and **why you're working** (packs).

## The Idea

Your terminal has incredible tools — Neovim, Yazi, fzf, lazygit, btop. But they don't talk to each other, don't remember where you left off, and can't adapt to whether you're writing code or producing music.

Nexus Shell is the orchestration layer that connects them.

```
┌──────────────────────────────────────────────────┐
│              nexus-daemon (Rust)                  │
│   State, events, dispatch, persistence.           │
│   No UI dependencies. Surface-agnostic.           │
│                                                   │
│   Surfaces        Capabilities       Packs        │
│   (WHERE)         (WHAT tools)       (WHY)        │
│                                                   │
│   tmux            Neovim             coding       │
│   Tauri desktop   Yazi               music        │
│   Sway/i3         fzf                writing      │
│   Web browser     Claude/AI          finance      │
│   Android         Reaper             ai-art       │
│   ...             ...                ...          │
└──────────────────────────────────────────────────┘
```

- **Surface**: anything that displays workspaces — tmux, a tiling WM, a Tauri app, a browser
- **Capability**: an abstract tool interface — editor, explorer, agent, menu, audio monitor
- **Pack**: a domain module — what tools, layouts, HUD modules, and automations a workflow needs

## Quick Start

```bash
git clone https://github.com/samir-alsayad/nexus-shell.git
cd nexus-shell/crates
cargo build --release

# Install binaries
cargo install --path nexus-daemon
cargo install --path nexus-cli

# Start using it (daemon auto-launches on first connect)
nexus hello
nexus session info
nexus pane list
```

### With tmux

```bash
nexus-daemon --mux tmux
tmux attach -t nexus
```

### With Tauri desktop

```bash
cd crates/nexus-tauri/ui && npm install
cd .. && cargo tauri dev
```

See [docs/USAGE.md](docs/USAGE.md) for full usage guide and [docs/INSTALLATION.md](docs/INSTALLATION.md) for prerequisites.

## Architecture

```
Surface (CLI / Tauri / tmux / Sway)
    │
    ▼  JSON-RPC 2.0 over Unix socket
nexus-daemon
    │
    ├── NexusCore (state, dispatch, events)
    ├── Capability Registry (adapters)
    ├── Surface Registry (mode + capabilities)
    ├── Session Persistence (auto-save every 30s)
    └── Mux Backend (NullMux or TmuxMux)
```

All state and logic live in the daemon. Surfaces are dumb renderers that connect over Unix sockets, declare their capabilities, and render from engine events.

### Crates

| Crate | Type | Purpose |
|-------|------|---------|
| `nexus-core` | lib | ABCs, adapters, event bus, capability contracts |
| `nexus-engine` | lib | NexusCore facade, workspace state, dispatch, persistence |
| `nexus-client` | lib | JSON-RPC client, auto-launch, event subscription |
| `nexus-daemon` | bin | Shared daemon (owns engine, Unix socket servers) |
| `nexus-cli` | bin | Thin CLI client |
| `nexus-tauri` | bin | Desktop app (Tauri framework) |
| `nexus-tmux` | lib | TmuxMux — real tmux backend via CLI |
| `nexus-editor` | lib | Editor capability adapters |

### Surface Modes

| Mode | PTY Owner | Surfaces |
|------|-----------|----------|
| **Delegated** | Mux backend (tmux, Sway) | tmux, i3/Sway, Hyprland |
| **Internal** | Engine PtyManager | Tauri, Web, Android |
| **Headless** | Engine PtyManager | CI, scripting, tests |

### Dispatch Domains

15 domains: `navigate`, `pane`, `stack`, `chat`, `pty`, `session`, `keymap`, `commands`, `layout`, `capabilities`, `nexus`, `fs`, `editor`, `surface`.

Any surface or script can call any domain via JSON-RPC:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"pane.list","params":null}' | \
  socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/nexus/nexus.sock
```

## Navigation

Modeless. `Alt` is the universal modifier.

| Key | Action |
|-----|--------|
| `Alt+h/j/k/l` | Move focus between panes |
| `Alt+m` | Open Command Graph (menu) |
| `Alt+n` | Push new tab onto stack |
| `Alt+w` | Pop active tab |
| `Alt+[` / `Alt+]` | Rotate through tabs |
| `Alt+v` / `Alt+s` | Split vertical / horizontal |
| `Alt+z` | Zoom pane |

Keybindings are engine-owned and fetched dynamically by surfaces via `keymap.get`.

## Key Concepts

### Tab Stacks

Every pane holds a **stack of tabs** — multiple tools layered on top of each other. Push a terminal on top of your editor, rotate back, push a chat agent. Workspaces persist across reboots with proportional geometry that adapts to any screen size.

### Command Graph

A unified command surface — every action, setting, and navigation target is a node in a scoped, searchable tree. Nodes resolve through a three-tier cascade: workspace > profile > global.

### Packs

Domain modules that define what a workflow needs:

| Pack | Tools | HUD | Automations |
|------|-------|-----|-------------|
| `rust-dev` | Neovim, cargo, bacon | Build status, test results | Save triggers test run |
| `music-production` | Reaper, audio monitor | BPM, levels, MIDI | File change triggers notify |
| `writing` | Neovim (prose), Pandoc | Word count, chapter progress | Save triggers export |

## Extension Model

Five levels of extensibility:

1. **Actions** — shell scripts with metadata. Drop in `.nexus/actions/`, appears in Command Graph.
2. **Menu Trees** — YAML files declaring Command Graph nodes. Pure data.
3. **Packs** — domain bundles (tools, connectors, menu nodes, keybinds).
4. **Modules** — adapter implementations (e.g., Helix editor adapter).
5. **Surfaces** — complete display layers (tmux, Tauri, Web).

Levels 1-3 are fully portable across surfaces. A pack written for tmux works on Tauri without modification.

## Requirements

- Rust toolchain (1.75+)
- Unix-like OS (Linux or macOS)
- Optional: tmux (for tmux surface), Node.js 18+ (for Tauri)

## Documentation

- [Installation](docs/INSTALLATION.md) — build from source, prerequisites
- [Usage Guide](docs/USAGE.md) — running the daemon, using each surface, troubleshooting
- [Architecture Theory](.gap/architecture.md) — three-layer model, extension hierarchy
- [Surface ABC Spec](.gap/specs/surface-abc.md) — surface modes, capabilities, protocol

## License

MIT
