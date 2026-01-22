# Parallax

A shell session management and workflow automation framework for ZSH. Parallax enables real-time synchronization between shell sessions, signal-based inter-process communication, and an interactive TUI dashboard for managing development workflows.

## Features

- **Session Sync (px-link)** - Automatically link shell sessions together for synchronized command execution
- **Signal-Based IPC** - Send commands between sessions using Unix signals (SIGUSR1/SIGUSR2)
- **Interactive Dashboard** - FZF-powered TUI for browsing actions, settings, and system status
- **Workflow Actions** - Scriptable actions with metadata annotations for the dashboard
- **Environment Management** - Isolated environment handling per session
- **TMUX Integration** - Native TMUX-based split-pane workflow

## Requirements

- macOS or Linux
- ZSH shell
- tmux
- fzf
- jq

## Installation

```bash
git clone https://github.com/samir-alsayad/parallax.git
cd parallax
./install.sh
```

This will:
1. Deploy Parallax to `~/.parallax/`
2. Create symlinks for `parallax`, `px-link`, `px-exec`
3. Add shell integration to your `~/.zshrc`

For development (symlinks instead of copies):
```bash
./install.sh --dev
```

## Quick Start

### Launch the Dashboard

```bash
parallax
```

This opens a TMUX session with:
- **Top pane**: Your shell (Stage) - linked automatically via px-link
- **Bottom pane**: Parallax Dashboard - interactive action browser

### Shell Integration

After installation, new shells automatically integrate via `px-link`:

```bash
# New terminal automatically shows:
# "Auto-linked to: ProjectName (PID)"
```

### Manual Session Linking

If you have multiple Parallax sessions, shells will prompt you to choose:

```bash
source px-link  # Or just open a new terminal
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SHELL SESSION                        │
│  source ~/.parallax/bin/px-link                        │
│  ↓                                                      │
│  TRAPUSR1() - Receives commands via signal             │
└─────────────────────┬───────────────────────────────────┘
                      │ SIGUSR1
                      ▼
┌─────────────────────────────────────────────────────────┐
│                PARALLAX DASHBOARD                       │
│  • Session discovery (/tmp/px-session-*.meta)          │
│  • Environment files (/tmp/px-env-*.sh)                │
│  • Signal files (/tmp/px-signal-*.sh)                  │
│  • FZF-based navigation                                │
└─────────────────────────────────────────────────────────┘
```

## Commands

| Command | Description |
|---------|-------------|
| `parallax` | Launch the dashboard |
| `px-link` | Shell integration (source this) |
| `px-exec <session_id> <action>` | Execute action in session context |

## Configuration

### User Config

Create `~/.parallax/config` to customize behavior:

```bash
# ~/.parallax/config
export PX_LAYOUT_STYLE="reverse"    # App-like layout (default: terminal)
export PX_HUD_PATH_STYLE="full"     # Show full paths (default: short)
export PX_VERBOSE="true"            # Enable debug output
export PX_SHOW_LEGEND="false"       # Hide footer legend
```

### Safety Settings

Control which paths are allowed for remote command execution:

```bash
export PX_ALLOWED_PATHS="$HOME:/tmp:/projects"  # Colon-separated
```

## Creating Actions

Actions are shell scripts with metadata annotations:

```bash
#!/bin/bash
# @parallax-action
# @name: My Custom Action
# @id: custom:action
# @description: Does something useful
# @icon: sparkles
# @param NAME: Your name

echo "Hello, $NAME!"
```

Place actions in:
- `~/.parallax/content/actions/` (global)
- `./.parallax/actions/` (project-local)

## Project Structure

```
parallax/
├── bin/
│   ├── parallax          # Main dashboard entry point
│   ├── px-link           # Shell integration (ZSH)
│   └── px-exec           # Action executor
├── lib/
│   ├── core/             # Core functionality
│   │   ├── session.py    # Session management
│   │   ├── wizard.py     # FZF UI helpers
│   │   └── pillars/      # Dashboard sections
│   ├── exec/             # Internal executables
│   └── modes/            # Dashboard display modes
├── content/
│   └── actions/          # Built-in actions
├── tmux/
│   └── tmux.conf.snippet # TMUX configuration
└── install.sh
```

## How It Works

### Signal-Based Command Execution

1. Dashboard writes command to `/tmp/px-signal-<pid>.sh`
2. Dashboard sends `SIGUSR1` to linked shell
3. Shell's `TRAPUSR1` reads and executes the command
4. Results appear in the shell

### Session Discovery

Sessions register at `/tmp/px-session-<pid>.meta`:
```
ProjectName|/path/to/project|12345|tmux-session
```

Shells discover sessions via glob and choose which to link.

## Troubleshooting

### Shell not linking

Make sure px-link is sourced:
```bash
source ~/.parallax/bin/px-link
```

### Dashboard not showing

Check tmux is installed:
```bash
tmux -V
```

### Actions not appearing

Verify action has correct metadata:
```bash
head -10 ~/.parallax/content/actions/my-action.sh
# Should show @parallax-action annotations
```

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## Related Projects

- [nexus-shell](https://github.com/samir-alsayad/nexus-shell) - VSCode-style terminal IDE built on Parallax
