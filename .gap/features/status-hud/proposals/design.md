# Design: Status HUD

## Architecture
A background "Status Service" iterates every 500ms, aggregates data, and pushes to a dedicated Tmux pane.

### 1. The HUD Pane
Created via `tmux new-window -n HUD -d "core/hud/renderer.sh"`. We will use Tmux `set-option -g status-format` or a dedicated pinned bottom pane.

### 2. Rendering (renderer.sh)
A loop that:
1.  Reads `jq` from `/tmp/nexus_telemetry.json`.
2.  Formats the string with ANSI colors based on `nxs-theme`.
3.  Uses `printf` to display the 1-liner.

### 3. Telemetry Schema
```json
{
  "agent": {
    "status": "thinking",
    "mission": "Workspace Engine"
  },
  "env": {
    "workspace": "Sovereign-Core",
    "profile": "swarm",
    "locality": "m1-local"
  }
}
```
