# Extending Parallax 🔌

Parallax is designed to be extended. You can add new capabilities by adding files to your library.

## 1. Creating Actions
Actions are executable scripts stored in `library/actions`.
- **Location**: `~/.parallax/library/actions` (Global) or `.parallax/library/actions` (Project).
- **Format**: Simple Action or Parameterized Action.

### Parameterized Action
Add `# params: var|Description|Default` comments to prompt for input.

```bash
#!/bin/bash
# params: name|Enter Persona Name|Ghost
# params: model|Select Model [gpt-4, claude-3, llama3]|gpt-4

echo "Creating persona $name with model $model..."
```

## 2. Creating Contexts
Contexts are YAML dictionaries that define lists of items.
- **Location**: `library/contexts`.
- **Example**: `my-tools.yaml`.

```yaml
# A custom context for freqent tools
items:
  - label: "Deploy to Prod"
    type: ACTION
    action: actions:deploy
  - label: "Production Logs"
    type: ACTION
    action: "kubectl logs -f deployment/app"
```

## 3. Creating Surfaces
Surfaces are Tmux layouts defined in YAML.
- **Location**: `library/surfaces`.

```yaml
# library/surfaces/monitor.yaml
layout: main-horizontal
panes:
  - command: "htop"
    size: 50%
  - command: "tail -f /var/log/syslog"
```
To activate: `px-surface apply monitor`.
