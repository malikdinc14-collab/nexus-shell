# Design: Multi-Folder Workspace Engine

## Architecture
Nexus will maintain a `NEXUS_WORKSPACES` environment variable containing a colon-separated list of active roots.

### 1. The Workspace Descriptor (`.nxs-workspace`)
```json
{
  "name": "Sovereign-Core",
  "roots": [
    "/Users/Shared/Projects/nexus-shell",
    "/Users/Shared/Projects/agents",
    "/Users/Shared/Projects/sovereign-inference"
  ],
  "settings": {
    "default_profile": "swarm"
  }
}
```

### 2. Search Orchestration
Update `core/search/lib/search_utils.sh`:
- Instead of searching `.`, search `${NEXUS_ROOTS[@]}`.
- If `NEXUS_ROOTS` is empty, default to `.`.

### 3. Daemon Orchestration
The `Daemon Manager` (Phase 5 precursor) will loop through the roots and spin up the necessary services for each.

## User Interface
- **Command**: `:workspace load <path>`
- **Menu**: New "Workspace" category in the `Alt-X` menu.
- **Visuals**: Folders will be color-coded in the Search TUI.
