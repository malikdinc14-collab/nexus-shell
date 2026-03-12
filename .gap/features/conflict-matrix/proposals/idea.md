# Idea: The Merge Conflict Matrix

## Problem Statement
Resolving merge conflicts in a terminal is a nightmare. VSCode has a clear advantage with its visual inline markers and comparison views. Nexus Shell needs to bridge this gap to remain "indestructible" for professional work.

## Proposed Solution
A "Conflict Matrix" mode that auto-triggers when a `git` operation fails due to conflicts. It hot-swaps the current layout for a 3-way split: `LOCAL` (Left), `REMOTE` (Right), and `MERGED/CURRENT` (Center/Bottom).

## Key Features
- **Auto-Invocation**: Triggered via `nxs-hook` on `post-rewrite` or `pre-rebase` failures.
- **Visual Clarity**: High-contrast diffing using specialized nvim/bat configurations.
- **Keyboard Efficiency**: Single-key shortcuts to pick segments (`L` for Local, `R` for Remote, `B` for Both).
- **Session Focus**: Locks the user into the Matrix until all conflicts are resolved or aborted.
