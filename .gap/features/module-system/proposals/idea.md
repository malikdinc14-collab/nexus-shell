# Idea: Module Install UX & Pack Enrichment

## Problem Statement
Packs currently only detect project markers and list tools. They don't define compositions, HUD modules, commands, connectors, or keybinds. There's no way to install, discover, or manage modules from the CLI.

## Proposed Solution
1. Enrich the Pack dataclass to support full domain definitions (compositions, HUD, commands, connectors, keybinds).
2. Add `nexus install/uninstall/search/update` CLI commands for module lifecycle management.
3. Define a `module.yaml` manifest standard for declaring module metadata and dependencies.

## Key Features
- **Pack enrichment**: Full pack spec with compositions, HUD modules, commands, connectors, LSP config, and keybinds.
- **Module manifest**: `module.yaml` declares name, version, type (pack/adapter/surface/bridge), dependencies.
- **Install from multiple sources**: Local path, git URL, or registry.
- **Module discovery**: `nexus search <query>` against curated index.
- **Dependency resolution**: Modules can declare dependencies on capabilities or other modules.
- **Update management**: `nexus update` checks and applies module updates.

## Target User
Power users who want to extend nexus-shell for their specific domain or workflow.
