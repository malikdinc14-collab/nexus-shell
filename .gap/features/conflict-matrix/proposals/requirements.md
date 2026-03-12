# Requirements: Merge Conflict Matrix (The Desktop Killer)

## Functional Requirements
1.  **Conflict Detection**: Detect when files have `<<<<<<<` markers.
2.  **TUI Layout**: Specifically requested a 3-way vertical or 2-up-1-down split.
3.  **Diff Engine**: Must use `nvim -d` (diff mode) but with a custom wrapper for better navigation.
4.  **Auto-Commit**: Offer to stage and commit resolved files automatically.
5.  **HUD Sync**: The Status HUD must turn **RED** while in Conflict mode.

## Technical Requirements
- **Git Hooks**: Must provide an `nxs-git-config` command to install hooks locally.
- **Tmux Composition**: Create `compositions/conflict_matrix.json`.

## Non-Functional Requirements
- **Isolation**: Prevent common terminal actions (like `:run`) while in a conflict state.
- **Indestructibility**: If the editor crashes, the resolution progress must be saved in Git's index.
