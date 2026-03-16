# Nexus Shell Extensions

Extensions add functionality to Nexus Shell without modifying the core system.

## Directory Structure

```
extensions/
├── loader.sh           # Extension manager (list, install, load)
└── <extension-name>/
    ├── manifest.yaml   # Extension metadata and capabilities
    ├── install.sh      # Installation script
    ├── bin/            # Executables added to PATH
    ├── hooks/          # Integration hooks
    ├── mcp/            # MCP server registration
    └── config/         # Default configuration
```

## Available Extensions

| Extension | Description | Status |
|-----------|-------------|--------|
| grepai | AI-powered semantic code search | Optional |

## Usage

### List Extensions

```bash
nxs extension list
```

### Install an Extension

```bash
nxs extension install grepai
```

### Get Extension Info

```bash
nxs extension info grepai
```

### Use an Extension

Once installed, extensions integrate automatically:

```bash
# grepai semantic search
nxs-grepai search "error handling"

# Call graph tracing
nxs-grepai trace callers "Login"

# Via unified search interface
nxs-search semantic "authentication flow"
```

## Creating Extensions

### 1. Create Directory

```bash
mkdir -p extensions/my-extension/{bin,hooks,mcp,config}
```

### 2. Create Manifest

```yaml
# extensions/my-extension/manifest.yaml
name: my-extension
version: 1.0.0
description: What it does
author: your-name
type: tool
binary: my-tool

install: install.sh
commands:
  - name: nxs-my-extension
    path: bin/nxs-my-extension

hooks:
  search_provider: hooks/search_provider.sh
```

### 3. Create Install Script

```bash
#!/bin/bash
# extensions/my-extension/install.sh
# Install your tool (brew, curl, pip, etc.)
```

### 4. Create Hooks

```bash
#!/bin/bash
# extensions/my-extension/hooks/search_provider.sh
QUERY="$1"
MODE="$2"
# Your implementation
```

## Extension Hooks

| Hook | Purpose |
|------|---------|
| `search_provider.sh` | Provides search capability to `nxs-search` |
| `menu_provider.sh` | Provides menu entries to Parallax |
| `boot_provider.sh` | Runs at station boot |

## MCP Integration

Extensions can register as MCP servers for AI agent integration:

```yaml
mcp:
  enabled: true
  server: "my-extension mcp"
  tools:
    - my_tool_name
```

## Configuration

User overrides go in `~/.nexus/extensions/<name>.yaml`.

## See Also

- [grepai Documentation](https://github.com/yoanbernabeu/grepai)
- [Nexus Shell Architecture](docs/ARCHITECTURE_ANALYSIS.md)
