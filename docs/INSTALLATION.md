# Installation

## Prerequisites

**Required:**
- Rust toolchain (rustup recommended): `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- A Unix-like OS (Linux or macOS)

**Optional (for specific surfaces):**

| Surface | Requirements |
|---------|-------------|
| tmux | `tmux` (any recent version) |
| Tauri desktop | `cargo install tauri-cli`, Node.js 18+, system WebView (WebKitGTK on Linux) |
| Sway/i3 | `swaymsg` or `i3-msg` (planned) |

**Optional (for full feature set):**
- `fzf` — fuzzy finder (used by some capabilities)
- `ripgrep` (`rg`) — fast search
- `fd` — file discovery
- Neovim — editor integration

## Building from Source

```bash
git clone https://github.com/samir-alsayad/nexus-shell.git
cd nexus-shell/crates
cargo build --release
```

Binaries are in `crates/target/release/`:
- `nexus-daemon` — the shared engine daemon
- `nexus` — CLI client

### Install to PATH

```bash
cd crates
cargo install --path nexus-daemon
cargo install --path nexus-cli
```

### Tauri Desktop App

```bash
cd crates/nexus-tauri/ui
npm install

cd ..
cargo tauri build    # production build
# or
cargo tauri dev      # development mode with hot-reload
```

## Quick Start

```bash
# Option A: Just start using it (daemon auto-launches)
nexus hello

# Option B: Start daemon explicitly
nexus-daemon                # headless (for Tauri/web)
nexus-daemon --mux tmux    # with tmux backend

# Use the CLI
nexus session info
nexus pane list
nexus layout show
```

See [USAGE.md](USAGE.md) for detailed usage across all surfaces.

## Linux (WebKitGTK for Tauri)

On Debian/Ubuntu:

```bash
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget \
  libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

On Arch:

```bash
sudo pacman -S webkit2gtk-4.1 base-devel curl wget openssl gtk3 librsvg libayatana-appindicator
```

## Verify Installation

```bash
# Check binaries
nexus-daemon --help
nexus --help

# Run tests
cd nexus-shell/crates
cargo test --workspace
```
