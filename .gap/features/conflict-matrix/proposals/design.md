# Design: Merge Conflict Matrix

## Architecture
1.  **Trigger**: `bin/nxs-hook git-conflict`
2.  **Resolution Shell**: A specialized TUI loop that iterates over conflicting files.

### 1. The Composition (`compositions/conflict_matrix.json`)
```json
{
  "name": "Conflict Matrix",
  "panes": [
    { "id": "local", "cmd": "nvim -R {file}.LOCAL", "size": "33%" },
    { "id": "merged", "cmd": "nvim {file}", "size": "34%", "focus": true },
    { "id": "remote", "cmd": "nvim -R {file}.REMOTE", "size": "33%" }
  ]
}
```

### 2. The Logic
- When triggered, `nxs` identifies conflicting files via `git diff --name-only --diff-filter=U`.
- For each file, it provisions the 3-way split.
- It injects custom nvim keybinds to jump between conflict hunks.

### 3. Verification
- Use mock conflict scenarios in `tests/fixtures/`.
