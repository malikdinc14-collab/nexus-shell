# Technical Design: Nexus Project Discovery (Phase 2)

**Status**: Draft for Implementation
**Objective**: Provide a unified "Search & Action" layer that spans the entire project.

---

## 1. Floating Command Palette (`nxs-cmd`)

The Command Palette is a high-fidelity overlay invoked via `Alt + \`.

### Implementation
- **UI**: `tmux display-popup -E -w 70% -h 50% "nxs-cmd"`
- **Engine**: `fzf --header="Nexus: Command Palette" --prompt="> "`
- **Source**: Aggregates all executables in `$NEXUS_BIN` and registered module commands.

### Interface (FZF / Gum)
- A centered pop-up or a dedicated pane at the top.
- Fuzzy matching on command titles and IDs.
- Shows the associated hotkey on the right (e.g., `M-g`).

---

## 2. Floating Project Search (`nxs-grep`)

A high-fidelity search engine using a centered popup.

### The "Search View" (FZF + Preview)
- **UI**: `tmux display-popup -E -w 90% -h 80% "nxs-grep"`
- **Engine**: `rg --line-number --column --color=always . | fzf --ansi --preview 'bat --style=numbers --color=always --highlight-line {2} {1}'`
- **Action**: Pressing `Enter` on a result publishes an event to the bus:
  `{"type": "EDITOR_OPEN_FILE", "path": "src/main.py", "line": 42}`
- **The Jump**: The Editor pane receives this and instantly swaps to the correct tab and line.

---

## 3. Symbol Search (`nxs-symbols`)

Quick jump to any function, class, or variable in the project.

### Implementation
- **Provider**: Uses `ctags` or Neovim's LSP symbols.
- **UI**: Similar to the Search view but scoped to declaration names.
- **Visuals**: Displays icons for symbol types (e.g., `(f)` for function, `(c)` for class).

---

## 4. Floating Keymap Viewer (`nxs-keys`)

To solve the "memorization" problem, all keybinds are stored in a central registry and displayed via FZF.

### Implementation
- **Invoke**: `Alt + ?`
- **UI**: `tmux display-popup -E -w 60% -h 40% "nxs-keys"`
- **Engine**: `fzf --header="Nexus: Keybindings Reference"`
- **Action**: Selecting a row shows the full command path and documentation.

## 5. Why This Matters
An IDE is only as good as its **Discovery Layer**. 
- Without this, the user has to remember that "Git is Alt+G" and "Manager is Alt+P."
- With this, the user just presses `Alt + \` and types "Git" or "Tab" to see every possibility.
