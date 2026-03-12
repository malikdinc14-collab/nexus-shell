# Plan: Multi-Folder Workspace Engine [AUTHORIZED]

## Executive Summary
This plan authorizes the creation of the multi-folder workspace orchestration layer.

## Authorized Models
- **Orchestrator**: Antigravity (Scribe/Merge)
- **Worker**: Gemini-Swarm (Implementation of core/search logic)

## Inference Locality
- **Local**: All Bash/JSON orchestration logic.

## Implementation Details
1. **Isolated Worktree**: `feat/workspace-engine`
2. **Key Files**:
    - `core/workspace/workspace_manager.sh` (NEW)
    - `core/search/live_grep.sh` (MODIFY)
    - `core/search/quick_find.sh` (MODIFY)

## Swarm Mission Statement
"Implement the `workspace_manager.sh` logic to parse `.nxs-workspace` files and update the search core to perform aggregate searches across all defined roots."

---
**Status**: DRAFT (Awaiting human approval via `gap gate approve`)
