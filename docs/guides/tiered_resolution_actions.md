# Sovereign Actions & Tiered List Resolution

Nexus Shell features a cascading resource discovery system that allows for portable identity while maintaining project-specific context.

## 🏔️ Tiered Resolution Logic

The system resolves lists and actions in the following priority order (lower number overrides higher):

1.  **Workspace**: `project/.nexus/lists/` — Mission-bound tools and local context.
2.  **Profile**: `~/.nexus/profiles/<active_profile>/lists/` — Role-specific tooling for your current persona.
3.  **Global**: `~/.nexus/lists/` — Baseline baseline identity across all stations.
4.  **Builtin**: `modules/menu/lists/` — Core system distribution tools.

## 🛠️ Custom Action Providers

You can add dynamic actions by placing an executable `.sh` script in any `lists/` subfolder.

### Provider Format
The script should output JSON objects (one per line):
```bash
#!/bin/bash
echo '{"label": "🚀 My Action", "type": "ACTION", "payload": "echo Hello World"}'
```

### Global Engine Actions
The standard AI Infrastructure management tools are located in `~/.nexus/lists/engine/`. This includes:
- **Agent Provisioning**
- **Model-Server Slot Management**
- **Generic Proxy Lifecycle**

## 🔧 User-Level Menu Priority
To override the default home menu, create `~/.nexus/home.yaml`. This allows you to prioritize high-level abstractions like "AI Infrastructure" over standard file navigation.
