---
trigger: always_on
glob: "**/*"
description: "Core AXIOM rules for Agentic Sovereignty in Nexus Shell."
---

# AXIOM: Agentic Protocol for Nexus Shell

You are Jules (or a supporting Nexus agent). To ensure the integrity of the Nexus Factory, you MUST follow these axioms:

## 1. The Gated Agent Protocol (GAP)
*   **No Un-Gated Implementation**: Never write code for a new feature without a corresponding `plan.md` in `.gap/features/`.
*   **Ledger First**: Before requesting review, ensure the `status.yaml` for your feature reflects your current phase.
*   **Isolation**: Always check if you are in a dedicated feature branch/worktree before destructive edits.

## 2. Lean Core Architecture
*   **Modules are Metadata**: Do NOT add scripts, binaries, or implementation files to `/modules`. Place only `manifest.json` there.
*   **Services are Submodules**: Any core engine modification (e.g., to Agent Zero) must be made within the `services/` directory and handled as a Git Submodule task.

## 3. Communication Pattern
*   **Proactive Search**: Use `grep` and `find` to discover manifests and hooks before assuming paths.
*   **Nexus UI Tokens**: Always look for `nxs-theme` tokens when writing UI-related bash scripts.
