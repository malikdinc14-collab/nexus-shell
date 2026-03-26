# Nexus Shell — Usage Guide

How to build, run, and use Nexus Shell across all supported surfaces.

---

## Building

All crates live under `crates/`. The workspace Cargo.toml is at `crates/Cargo.toml`.

```bash
cd nexus-shell/crates
cargo build --release
```

This produces three binaries in `target/release/`:

| Binary | Purpose |
|--------|---------|
| `nexus-daemon` | Shared engine over Unix sockets (must be running) |
| `nexus` | Thin CLI client |
| `nexus-tauri` | Desktop app (Tauri) |

Install them to your PATH:

```bash
cargo install --path nexus-daemon
cargo install --path nexus-cli
```

---

## Architecture Overview

```
Surface (CLI / Tauri / tmux / Sway)
    |
    v  JSON-RPC over Unix socket
nexus-daemon  (owns NexusCore — all state lives here)
    |
    +-- command socket:  ~/.local/share/nexus/nexus.sock
    +-- event socket:    ~/.local/share/nexus/nexus-events.sock
    +-- PID file:        ~/.local/share/nexus/nexus.pid
```

Surfaces are dumb renderers. All logic, state, keybindings, and commands live in the daemon.

---

## 1. Running the Daemon

### Headless (no multiplexer)

```bash
nexus-daemon
```

The daemon starts with `NullMux` — no terminal multiplexer. Suitable for Tauri, web, or CLI-only usage. PTY management is handled by the engine's internal `PtyManager`.

### With tmux backend

```bash
nexus-daemon --mux tmux
```

Starts with `TmuxMux` — the daemon drives a real tmux session. PTY ownership is delegated to tmux. Use this when your primary surface is a terminal.

### Custom socket path

```bash
nexus-daemon --socket /tmp/my-nexus/nexus.sock
```

### Auto-launch

You don't need to start the daemon manually. When any client (`nexus` CLI, Tauri app) calls `NexusClient::connect()`, it auto-launches the daemon if no socket is found. The client polls for up to 3 seconds for the daemon to come up.

To force a specific mux mode with auto-launch, set the environment variable:

```bash
export NEXUS_DAEMON_ARGS="--mux tmux"
```

---

## 2. CLI Surface

The `nexus` CLI is a thin JSON-RPC client. Every command is a single request to the daemon.

### Basic commands

```bash
# Check daemon is running
nexus hello

# Session info
nexus session info

# List panes
nexus pane list

# Show layout tree
nexus layout show
```

### Layout operations

```bash
# Split current pane
nexus layout split --direction vertical
nexus layout split --direction horizontal --pane-type terminal

# Navigate between panes
nexus layout navigate left
nexus layout navigate right
nexus layout navigate up
nexus layout navigate down

# Focus a specific pane
nexus layout focus <pane-id>

# Toggle zoom on focused pane
nexus layout zoom
```

### Stack operations

```bash
# Push a tab onto a pane's stack
nexus stack push --identity <pane-id> --pane-id <pane-id> --name "My Tab"

# Switch to a tab by index
nexus stack switch --identity <pane-id> --index 1

# Close top tab
nexus stack close --identity <pane-id>

# Tag and rename
nexus stack tag --identity <pane-id> --tag "editor"
nexus stack rename --identity <pane-id> --name "Main Editor"
```

### Session persistence

```bash
# Sessions auto-save every 30 seconds
# Manual operations:
nexus session create --name myproject --cwd /path/to/project
nexus session list
nexus session info
```

### Raw dispatch (any engine command)

The CLI wraps common operations, but you can send any dispatch command directly using the JSON-RPC protocol:

```bash
# Using socat for raw JSON-RPC
echo '{"jsonrpc":"2.0","id":1,"method":"surface.list","params":null}' | \
  socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/nexus/nexus.sock

echo '{"jsonrpc":"2.0","id":1,"method":"fs.list","params":{"path":"."}}' | \
  socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/nexus/nexus.sock

echo '{"jsonrpc":"2.0","id":1,"method":"capabilities.list","params":null}' | \
  socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/nexus/nexus.sock
```

Available dispatch domains: `navigate`, `pane`, `stack`, `chat`, `pty`, `session`, `keymap`, `commands`, `layout`, `capabilities`, `nexus`, `fs`, `editor`, `surface`.

---

## 3. Tauri Desktop Surface

### Prerequisites

```bash
# Install Tauri CLI
cargo install tauri-cli

# Install frontend dependencies
cd crates/nexus-tauri/ui
npm install
```

### Running

```bash
cd crates/nexus-tauri
cargo tauri dev
```

This starts the Tauri app which:
1. Auto-launches `nexus-daemon` if not already running
2. Connects to the daemon's command socket
3. Subscribes to the event socket for live updates
4. Renders the workspace layout with embedded terminal panes

### How it works

- **Layout**: Fetched from daemon via `layout.show`, updated via `layout-changed` events
- **Keybindings**: Fetched from daemon via `keymap.get`, applied dynamically
- **Command palette**: Commands from `commands.list`, dispatched through engine
- **File explorer**: Reads filesystem through `fs.list` / `fs.read` dispatch
- **Editor**: Opens files via `editor.open` events (no global hacks)
- **Chat backends**: Discovered via `capabilities.list`

The Tauri surface is an **Internal** mode surface — it renders its own UI from engine state and events. PTYs are managed by the engine's `PtyManager`, not tmux.

### Testing the Tauri surface

1. Start the daemon: `nexus-daemon` (headless mode, no `--mux` needed)
2. Run Tauri: `cd crates/nexus-tauri && cargo tauri dev`
3. Verify with CLI alongside: `nexus pane list` should show same state

---

## 4. tmux Surface (Delegated Mode)

The tmux surface uses **Delegated** mode — the daemon drives tmux directly. tmux owns the terminal panes and PTYs.

### Running

```bash
# Start daemon with tmux backend
nexus-daemon --mux tmux

# The daemon creates a tmux session named "nexus"
# Attach to it:
tmux attach -t nexus
```

### How it works

- `TmuxMux` calls `tmux` CLI commands (`new-session`, `split-window`, `send-keys`, etc.)
- Pane operations in the engine map to real tmux pane operations
- Tags stored as tmux pane options (`@key`) with in-process cache
- HUD rendered via tmux `status-left` / `status-right`
- Popups use `tmux display-popup`
- Menus use `tmux display-menu`

### Using with an isolated tmux server

```bash
# Use a dedicated tmux socket (avoids conflicts with your main tmux)
nexus-daemon --mux tmux --socket /tmp/nexus-dev/nexus.sock
```

The `TmuxMux` supports socket labels via `TmuxMux::with_socket("label")`. To pass this through the daemon, set the socket label in the future via configuration (currently defaults to the user's default tmux server).

### Keybindings for tmux

When running through tmux, bind keys in your `tmux.conf` to call the `nexus` CLI:

```tmux
# Alt+h/j/k/l navigation
bind -n M-h run-shell 'nexus layout navigate left'
bind -n M-j run-shell 'nexus layout navigate down'
bind -n M-k run-shell 'nexus layout navigate up'
bind -n M-l run-shell 'nexus layout navigate right'

# Alt+v/s splits
bind -n M-v run-shell 'nexus layout split --direction vertical'
bind -n M-s run-shell 'nexus layout split --direction horizontal'

# Alt+z zoom
bind -n M-z run-shell 'nexus layout zoom'

# Alt+w close pane
bind -n M-w run-shell 'nexus pane close --pane-id "$(tmux display -p "#{pane_id}")"'
```

### CLI + tmux together

You can use the CLI while attached to the tmux session:

```bash
# In another terminal (or tmux pane):
nexus layout show          # See the layout tree
nexus pane list            # List all panes
nexus session info         # Session metadata
```

---

## 5. Sway / i3 / Hyprland (WM Orchestrator Mode)

> Status: Planned (Phase 7D). The Surface ABC is in place; the WM surface is not yet implemented.

The vision: instead of running inside a terminal multiplexer, Nexus orchestrates your tiling window manager directly.

### How it will work

- **Surface mode**: Delegated (same as tmux — the WM owns the windows)
- **SwayMux** adapter implementing the `Mux` trait via Sway IPC (`swaymsg`)
- Pane operations map to Sway container operations
- `create_container` → `swaymsg exec <terminal>`
- `split` → `swaymsg splith/splitv`
- `focus` → `swaymsg focus left/right/up/down`
- `resize` → `swaymsg resize`
- `destroy_container` → `swaymsg kill`

### Current workaround: Sway + tmux

Until the native Sway surface exists, you can use Nexus through tmux inside Sway:

```bash
# Start daemon with tmux
nexus-daemon --mux tmux

# Open your terminal emulator (foot, alacritty, kitty)
# Attach to the nexus tmux session
tmux attach -t nexus
```

You can also bind Sway keys to nexus CLI commands:

```sway
# In ~/.config/sway/config
# Nexus navigation (when focused on nexus terminal)
bindsym $mod+h exec nexus layout navigate left
bindsym $mod+j exec nexus layout navigate down
bindsym $mod+k exec nexus layout navigate up
bindsym $mod+l exec nexus layout navigate right
```

---

## 6. Surface Registration Protocol

Surfaces register with the engine on connect, declaring their mode and capabilities:

```bash
# Register a surface (via raw JSON-RPC)
echo '{"jsonrpc":"2.0","id":1,"method":"surface.register","params":{
  "id": "my-surface-1",
  "name": "My Custom Surface",
  "mode": "Internal",
  "capabilities": {
    "popup": false, "menu": true, "hud": true, "rich_content": true,
    "internal_tiling": true, "external_tiling": false,
    "detachable_panes": false, "transparency": false, "gaps": false,
    "multi_window": false, "keyboard": true, "mouse": true,
    "touch": false, "persistent": true, "multi_client": false,
    "reconnectable": true, "notifications": true
  }
}}' | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/nexus/nexus.sock
```

### Surface modes

| Mode | PTY Owner | Example Surfaces |
|------|-----------|-----------------|
| **Delegated** | Mux backend (tmux, Sway) | tmux, i3/Sway, Hyprland |
| **Internal** | Engine PtyManager | Tauri, Web, Android |
| **Headless** | Engine PtyManager | CI, scripting, tests |

Rules:
- Only one Delegated surface at a time
- Multiple Internal surfaces can coexist with one Delegated
- Multiple Internal surfaces can coexist with each other

### Query surfaces

```bash
# List connected surfaces
nexus hello  # or raw: surface.list

# Get active mode
echo '{"jsonrpc":"2.0","id":1,"method":"surface.mode","params":null}' | \
  socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/nexus/nexus.sock

# Get aggregate capabilities
echo '{"jsonrpc":"2.0","id":1,"method":"surface.capabilities","params":null}' | \
  socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/nexus/nexus.sock
```

---

## 7. Event Subscription

Surfaces (and scripts) can subscribe to engine events via the event socket:

```bash
# Stream all events
socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/nexus/nexus-events.sock

# Events are newline-delimited JSON:
# {"event":"layout.changed","data":{...}}
# {"event":"pty.output","data":{"pane_id":"...","data":"..."}}
# {"event":"stack.changed","data":{...}}
# {"event":"editor.file_opened","data":{"path":"...","name":"..."}}
```

---

## 8. Troubleshooting

### Daemon won't start

```bash
# Check if already running
cat $XDG_RUNTIME_DIR/nexus/nexus.pid 2>/dev/null && echo "PID file exists"
ls $XDG_RUNTIME_DIR/nexus/nexus.sock 2>/dev/null && echo "Socket exists"

# Kill stale daemon
kill $(cat $XDG_RUNTIME_DIR/nexus/nexus.pid) 2>/dev/null

# Remove stale files (daemon does this on startup, but just in case)
rm -f $XDG_RUNTIME_DIR/nexus/nexus.sock $XDG_RUNTIME_DIR/nexus/nexus-events.sock

# Start fresh
nexus-daemon
```

### Socket path

The default socket location depends on your system:
- Linux: `$XDG_RUNTIME_DIR/nexus/nexus.sock` (typically `/run/user/1000/nexus/`)
- Fallback: `/tmp/nexus-<uid>/nexus.sock`

Override with `--socket`:

```bash
nexus-daemon --socket /tmp/my-nexus/nexus.sock
```

### CLI can't connect

```bash
# Verify daemon is listening
nexus hello

# If "Failed to connect", the daemon isn't running
# The client will try to auto-launch it
# Check daemon stderr for errors:
nexus-daemon 2>&1 | head -20
```

### tmux mode issues

```bash
# Verify tmux is installed
tmux -V

# Start daemon with tmux debug output
nexus-daemon --mux tmux 2>&1

# Check if tmux session was created
tmux list-sessions

# Attach manually
tmux attach -t nexus
```

### Multiple surfaces

```bash
# Run daemon (headless or tmux)
nexus-daemon

# Terminal 1: attach tmux surface
nexus-daemon --mux tmux  # (restart with tmux if needed)
tmux attach -t nexus

# Terminal 2: run Tauri
cd crates/nexus-tauri && cargo tauri dev

# Terminal 3: use CLI
nexus pane list
nexus layout show
```

### Running tests

```bash
cd crates

# All tests
cargo test --workspace

# Specific crate
cargo test -p nexus-engine
cargo test -p nexus-core
cargo test -p nexus-tmux

# tmux integration tests (requires tmux installed)
cargo test -p nexus-tmux -- --ignored
```
