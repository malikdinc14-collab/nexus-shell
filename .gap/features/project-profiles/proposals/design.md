# Design: Project Profiles

## Implementation
1.  **Directory**: `config/profiles/`
2.  **Variables**: Create `core/engine/env/profile_loader.sh` to handle the logic.

### 1. Spec (`config/profiles/swarm.yaml`)
```yaml
name: "Swarm Orchestration"
theme: "dracula"
composition: "ai-pair"
daemons:
  - agent-zero
  - lsp-python
env:
  GAP_APPROVAL_MODE: "auto"
```

### 2. The Switcher (`:profile`)
The command will:
1.  Read the YAML using `yq`.
2.  Source the new theme.
3.  Execute `nxs load-composition`.
4.  Signal the Daemon Manager to reconcile running services.
