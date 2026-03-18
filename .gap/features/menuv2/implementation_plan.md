# Implementation Plan - V5: Menu Content Design & Pillar Refinement

Establish the core content structure for the Nexus Menu, mapping functional pillars to cascading data sources.

## Core Pillars & Strategy

| Pillar | Policy | Primary Sources | Specialized Provider |
| :--- | :--- | :--- | :--- |
| **Places** | `aggregate` | `$NEXUS_HOME/places`, `$PROJECT_ROOT` | `jump.sh` (Recent/Frecent) |
| **Notes** | `aggregate` | `$NEXUS_HOME/notes`, `$PROJECT_ROOT/.nexus/notes` | `daily_log.py` |
| **Build** | `override` | `$PROJECT_ROOT/.nexus/build/*.sh` | `action_resolver.py` |
| **Specs** | `aggregate` | `$PROJECT_ROOT/docs/specs`, `$PROJECT_ROOT/design` | - |
| **Tasks** | `aggregate` | `$PROJECT_ROOT/task.md` | `task_provider.py` |
| **Recent** | `override` | - | `nxs-flight-recorder --recent` |

## Proposed Changes

### [Component: Menu Content]

#### [MODIFY] [home.yaml](file:///Users/Shared/Projects/nexus-shell/modules/menu/config/home.yaml)
Update the root menu to reflect these official pillars.

#### [MODIFY] [lists.yaml](file:///Users/Shared/Projects/nexus-shell/config/lists.yaml)
Map the context keys to the multi-layered sources defined above.

#### [NEW] [task_provider.py](file:///Users/Shared/Projects/nexus-shell/core/engine/api/providers/task_provider.py)
A script provider that parses the local [task.md](file:///Users/samir/.gemini/antigravity/brain/ddcc162d-1179-4e23-9914-d9fc5982f9ea/task.md) and emits menu items representing active sub-tasks.

### [Component: UI Governance]
#### [MODIFY] [nxm.py](file:///Users/Shared/Projects/nexus-shell/modules/menu/bin/nxm.py)
- Ensure icons for `NOTE`, `ACTION`, and `FOLDER` types are consistent with the pillar design.

## Verification Plan

### Manual Verification
- Navigate to "Tasks" and verify it correctly parses the current [task.md](file:///Users/samir/.gemini/antigravity/brain/ddcc162d-1179-4e23-9914-d9fc5982f9ea/task.md).
- Navigate to "Places" and verify it shows both global bookmarks and project folders.
- Verify "Build" correctly overrides global build actions with project-specific ones.
