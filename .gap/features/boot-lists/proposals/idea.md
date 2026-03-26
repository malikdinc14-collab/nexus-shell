# Idea: Project Boot Lists (`.nexus/boot.yaml`)

## Problem Statement
Workspaces require manual setup every time: starting dev servers, loading AI models, running migrations. There's no way to declare "when I open this project, do these things."

## Proposed Solution
A `.nexus/boot.yaml` file in any project root that declares ordered startup actions. The boot_loader discovers and executes these on workspace attach via the Command Graph's workspace layer.

## Key Features
- **Ordered execution**: Items run sequentially by default, with `wait: true/false` controlling blocking behavior.
- **Health checks**: Optional `health` URL polled until the service is ready before proceeding.
- **Background processes**: Long-running services (dev servers, model slots) tracked and killed on workspace detach.
- **HUD integration**: Boot progress displayed in the Status HUD during startup.
- **Project menus**: Companion `.nexus/menu.yaml` injects project-specific commands into the Command Graph.

## Integration Points
- Command Graph 3-layer cascade (workspace layer)
- Boot loader (`core/kernel/boot/boot_loader.sh`)
- Momentum system (save/restore boot state)
- Model-server bridge (boot lists can create AI model slots)

## Target User
Any developer who works across multiple projects with different infrastructure requirements.
