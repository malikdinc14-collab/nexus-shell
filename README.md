# Nexus-Shell

**Transform your terminal into a powerhouse.** Nexus-Shell is a modular, high-performance terminal IDE built on TMUX, powered by the **Parallax** automation engine.

![Nexus-Shell Preview](./preview.png)

A VSCode-style terminal IDE with a focus on speed, modularity, and "indestructible" workflows. Features a multi-pane layout with Neovim, Yazi, integrated terminal, and optional AI chat.

## Features

- **Indestructible Panes**: Tools exit gracefully into a hub menu - panes never die
- **VSCode Workflow**: `edit file.txt` from terminal opens in editor pane
- **Render Mode**: `view file.md` shows rendered markdown with Glow
- **Modal Controls**: Alt-Esc for navigation/resizing, Ctrl+\ for commands
- **Themes**: Multiple color schemes (nexus-cyber, dracula, nord, etc.)
- **Modular Tools**: Use downloaded binaries or your system tools
- **Optional AI Chat**: Configure any chat tool or disable the chat pane

## Requirements

- [Parallax](https://github.com/samir-alsayad/parallax) - Shell session management (required)
- tmux
- fzf
- macOS or Linux

## Installation

```bash
git clone --recursive https://github.com/samir-alsayad/nexus-shell.git
cd nexus-shell
./install.sh
```

The installer will:
1.  Initialize and install the **Parallax** submodule
2.  Optionally download tools (nvim, yazi, glow, gum)
3.  Set up Nexus-specific Parallax actions
4.  Configure shell integration

The installer will ask:
- **Download tools?** - Downloads nvim, yazi, glow to `~/.nexus-shell/bin/`
- **Use system tools?** - Uses nvim, yazi, glow from your PATH

## Usage

```bash
# Start nexus in current directory
cd ~/my-project
nexus

# Or use the short alias
nxs
```

## Commands

### Parallax Integration (Deep Mode)

Nexus-Shell is powered by **Parallax**. Use `Alt+P` to open the Parallax dashboard as a popup overlay.

| Key | Action |
|-----|--------|
| `Alt+P` | Open Parallax Dashboard |
| `Ctrl+Shift+A` | Quick Actions Menu |
| `:px` | Open Parallax (Command) |
| `:a` | Quick Actions (Command) |

Configure the Parallax UI in `~/.config/nexus-shell/tools.conf`:
```bash
NEXUS_PX_UI="gum"   # Use sleek gum popups
NEXUS_PX_UI="tmux"  # Use standard tmux dashboard (default)
```

### Global (Ctrl+\ then type)

| Command | Action |
|---------|--------|
| `:q` | Quit (checks for unsaved changes) |
| `:wq` | Save all and quit |
| `:q!` | Force quit |
| `:v` | Toggle Editor/Render mode |
| `:theme` | Change color theme |
| `:help` | Show all commands |

### Navigation (Alt-Esc first, then)

| Key | Action |
|-----|--------|
| `n` | Focus Navigator (Tree) |
| `e` | Focus Editor |
| `t` | Focus Terminal |
| `c` | Focus Chat |
| `Shift+H/J/K/L` | Resize panes |
| `Esc` | Exit navigation mode |

### From Terminal Pane

```bash
edit file.txt    # Open file in editor pane
view readme.md   # Show rendered markdown
```

## Configuration

### Tool Configuration

Edit `~/.config/nexus-shell/tools.conf`:

```bash
# Use custom editor
NEXUS_EDITOR="/path/to/nvim"

# Use different file navigator
NEXUS_FILES="ranger"

# Enable AI chat pane (e.g., with aider, opencode)
NEXUS_CHAT="aider"

# Or disable chat pane entirely
NEXUS_CHAT=""
```

### Themes

Available themes:
- `nexus-cyber` (default) - Cyan on dark
- `ghost-noir` - Black and white
- `axiom-amber` - Warm amber tones
- `dracula` - Classic purple
- `nord` - Arctic blue
- `the-void` - Blood red on black

Change with `:theme` command inside Nexus.

### Creating Custom Themes

Create a JSON file in `~/.config/nexus-shell/themes/`:

```json
{
  "name": "my-theme",
  "bg": "#000000",
  "fg": "#ffffff",
  "accent": "#00ff00",
  "border": "#333333"
}
```

## Directory Structure

```
~/.config/nexus-shell/
├── tools.conf         # Tool configuration
├── tmux/              # TMUX configuration
├── themes/            # Color themes
└── scripts/           # Core scripts

~/.nexus-shell/bin/    # Downloaded binaries (if using download option)
```

## Architecture

Nexus-Shell is built on:
- **TMUX** - Terminal multiplexer for pane management
- **Parallax** - Shell session sync and integration
- **Neovim** - Editor with RPC support for remote commands
- **Yazi** - Fast file navigator
- **FZF** - Interactive selection menus

## Troubleshooting

### Panes not showing correctly

Make sure tmux is installed:
```bash
tmux -V
```

### Editor commands not working

Verify Neovim has RPC support:
```bash
nvim --version | grep -i "build type"
```

### Chat pane not appearing

Set `NEXUS_CHAT` in your tools.conf:
```bash
echo 'NEXUS_CHAT="opencode"' >> ~/.config/nexus-shell/tools.conf
```

## Uninstalling

```bash
# From the nexus-shell directory
./uninstall.sh
```

## Related Projects

- [Parallax](https://github.com/samir-alsayad/parallax) - Shell session management framework

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

Contributions welcome! Please open an issue or PR.
