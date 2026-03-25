# Nexus Shell Extensions

Extensions add functionality to Nexus Shell without modifying the core system.

## Quick Start

```bash
# First-time setup (detects installed tools, configures roles)
nxs wizard

# List all extensions
nxs extension list

# View your profile
nxs profile show

# Run health check
nxs doctor
```

## Architecture

**Core (Never Extensions):**
- `tmux` - Terminal multiplexer
- `python3` - Runtime
- `zsh`/`bash` - Shell

**Everything Else:** Extension with smart detection

## Directory Structure

```
extensions/
├── loader.sh           # Extension manager
├── .registry.json      # Auto-generated index
│
├── editor/             # nvim, helix, micro, code
├── explorer/           # yazi, nnn, ranger, lf
├── chat/               # opencode, gptme
├── terminal/           # zellij
├── viewer/             # glow, bat, view
├── search/             # grepai, television, ripgrep
├── devops/             # k9s, lazydocker, lazygit, dive
├── ai/                 # optillm, openevolve
├── monitor/            # btop, bottom, glances, bandwhich
├── media/              # ncspot, cava, spotify-player
├── database/           # harlequin, lazysql, sc-im
├── network/            # termshark, trippy, termscp
├── git/                # lazygit, gh-dash, serie
└── utility/            # fzf, gum, presenterm, etc.
```

## Available Extensions

| Category | Extensions |
|----------|------------|
| **Editor** | nvim ✓, helix, micro, code |
| **Explorer** | yazi ✓, nnn, ranger, lf |
| **Chat** | opencode ✓, gptme |
| **Terminal** | zellij |
| **Viewer** | glow, bat ✓, view |
| **Search** | grepai, television, ripgrep ✓ |
| **DevOps** | k9s, lazydocker, lazygit ✓, dive, process-compose |
| **AI** | optillm, openevolve |
| **Monitor** | btop ✓, bottom, glances, bandwhich |
| **Media** | ncspot, cava, spotify-player |
| **Database** | harlequin, lazysql, sc-im |
| **Network** | termshark, trippy, termscp |
| **Git** | lazygit, gh-dash, serie |
| **Utility** | fzf ✓, gum, presenterm, slumber, posting, taskwarrior-tui, visidata |

✓ = detected as installed

## Commands

### Extension Management

```bash
nxs extension list              # List all extensions
nxs extension list-all          # Detailed list for fzf
nxs extension categories        # Show all categories
nxs extension info <name>       # Show extension details
nxs extension install <name>    # Install an extension
```

### Profile Management

```bash
nxs profile show                # Display current profile
nxs profile edit                # Open in $EDITOR
nxs profile reset               # Delete and reconfigure
nxs profile detect              # Re-detect installed tools
nxs profile roles               # Show configured roles
```

### System

```bash
nxs wizard                      # Run first-run wizard
nxs doctor                      # Health check
```

## Creating Extensions

### 1. Create Directory

```bash
mkdir -p extensions/<category>/<name>
```

### 2. Create Manifest

```yaml
# extensions/editor/my-editor/manifest.yaml
name: my-editor
version: 1.0.0
type: tool
category: editor
description: My custom editor
author: your-name
license: MIT

binary: my-editor
role: editor
role_priority: 50

install:
  macos:
    - brew install my-editor
  linux:
    - sudo apt install my-editor
```

### 3. Add Install Script (Optional)

```bash
#!/bin/bash
# extensions/editor/my-editor/install.sh

if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install my-editor
else
    curl -sSL https://my-editor.dev/install.sh | sh
fi
```

### 4. Add Hooks (Optional)

```bash
#!/bin/bash
# extensions/editor/my-editor/hooks/role_provider.sh

# This hook is called when the editor role is needed
exec my-editor "$@"
```

## Profile System

**Location:** `~/.nexus/profile.yaml`

```yaml
version: 1
created: 2026-03-16

detected:
  editor: nvim
  explorer: yazi
  
roles:
  editor: nvim
  explorer: yazi
  chat: opencode
  terminal: zellij
  viewer: glow
  search: grepai

extensions:
  - grepai
  - lazygit

preferences:
  first_run_complete: true
```

### Priority Hierarchy

1. **Environment Variables** (highest)
   ```bash
   NEXUS_EDITOR=helix nxs boot
   ```

2. **User Profile** (`~/.nexus/profile.yaml`)

3. **Detected Tools** (auto-detected)

4. **System Fallbacks** (lowest: vi, ls, cat)

## See Also

- [Extension Architecture](docs/EXTENSION_ARCHITECTURE.md)
- [Architecture Analysis](docs/ARCHITECTURE_ANALYSIS.md)
- [Master Manual](docs/MASTER_MANUAL.md)
