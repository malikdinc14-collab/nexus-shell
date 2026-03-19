# SPEC: Quantum Splits
> Ready to execute. Verified against existing codebase.

---

## WHAT THIS IS

"Quantum Splits" = context-aware pane splitting that:
1. Infers WHAT to put in the new pane based on context (current role, active project)
2. Offers an inline picker (not a full menu) for quick selection
3. Respects the composition system — new panes get assigned a stack identity

Currently `M-v` and `M-s` just do raw tmux splits with no role assignment.

---

## DESIGN

### Keybinds
```
M-v  → quantum hsplit (currently raw split — needs upgrade)
M-s  → quantum vsplit (currently raw split — needs upgrade)
```

### Behavior
```
User presses M-v →
  1. Get current pane role (tmux #{@nexus_stack_id})
  2. Show inline mini-picker with 4-6 context-relevant options
  3. User picks (or escapes for bare split)
  4. Split + assign role via: stack push local "<cmd>" "<role>"
```

### Context-aware suggestions
| Current pane role | Suggested new pane options |
|------------------|---------------------------|
| `editor`         | terminal, files, chat, test-runner |
| `terminal`       | editor, chat, second-terminal |
| `files`          | editor, preview, chat |
| `chat`           | editor, terminal |
| anything else    | editor, terminal, chat, files |

---

## IMPLEMENTATION

### Step 1: Create `core/engine/api/quantum_split.py`

```python
#!/usr/bin/env python3
# core/engine/api/quantum_split.py
"""
Quantum Splits — context-aware pane splitting.
Called by: M-v (horizontal) and M-s (vertical)
Usage: quantum-split h|v
"""
import os, sys, subprocess
from pathlib import Path

NEXUS_HOME = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[3]))
STACK_BIN  = NEXUS_HOME / "core/kernel/stack/stack"

SUGGESTIONS = {
    "editor":   ["terminal", "chat", "files", "test-runner"],
    "terminal": ["editor", "chat", "terminal"],
    "files":    ["editor", "chat", "preview"],
    "chat":     ["editor", "terminal"],
    "menu":     ["editor", "terminal", "files"],
}
DEFAULT_SUGGESTIONS = ["editor", "terminal", "chat", "files"]

def get_current_role() -> str:
    try:
        return subprocess.check_output(
            ["tmux", "display-message", "-p", "#{@nexus_stack_id}"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return ""

def pick_role(suggestions: list[str]) -> str:
    """Show fzf inline picker. Returns role or empty string."""
    try:
        result = subprocess.run(
            ["fzf", "--height=8", "--reverse", "--prompt=Split as: ",
             "--bind=esc:abort"],
            input="\n".join(suggestions + ["(bare split)"]),
            capture_output=True, text=True
        )
        choice = result.stdout.strip()
        return "" if choice == "(bare split)" else choice
    except FileNotFoundError:
        return ""

def main():
    direction = sys.argv[1] if len(sys.argv) > 1 else "h"
    flag = "-h" if direction == "h" else "-v"

    current_role = get_current_role()
    suggestions = SUGGESTIONS.get(current_role, DEFAULT_SUGGESTIONS)
    role = pick_role(suggestions)

    from engine.capabilities.registry import REGISTRY
    from engine.capabilities.base import CapabilityType

    mux = REGISTRY.get_best(CapabilityType.MULTIPLEXER)
    if not mux:
        # Fallback: raw tmux split
        subprocess.run(["tmux", "split-window", flag])
        return

    # Split + assign role
    current_window = subprocess.check_output(
        ["tmux", "display-message", "-p", "#{session_name}:#{window_index}"],
        stderr=subprocess.DEVNULL
    ).decode().strip()

    new_pane = mux.split(current_window, direction=direction)
    if new_pane and role:
        from engine.api.nexus_ctl import execute_plan
        from engine.api.intent_resolver import IntentResolver
        plan = IntentResolver().resolve("run", "ROLE", role, "replace", "terminal")
        plan["window"] = current_window
        plan["strategy"] = "stack_replace"
        execute_plan(plan, str(NEXUS_HOME))

if __name__ == "__main__":
    sys.exit(main() or 0)
```

### Step 2: Add symlink
```bash
ln -sf ../core/engine/api/quantum_split.py bin/quantum-split
chmod +x core/engine/api/quantum_split.py
```

### Step 3: Update keybinds in `config/keybinds/active.conf`

Change:
```
bind-key -n 'M-v' split-window -h -c "#{pane_current_path}" \; set-option ...
bind-key -n 'M-s' split-window -v -c "#{pane_current_path}" \; set-option ...
```

To:
```
bind-key -n 'M-v' run-shell "${NEXUS_HOME}/bin/quantum-split h"
bind-key -n 'M-s' run-shell "${NEXUS_HOME}/bin/quantum-split v"
```

---

## FALLBACK BEHAVIOR

If fzf is not available OR user presses Escape → do raw split with no role assignment.
This preserves M-v / M-s for power users who just want a clean split.

---

## FILES

| # | File | Action |
|---|------|--------|
| 1 | `core/engine/api/quantum_split.py` | Create (~80 lines) |
| 2 | `bin/quantum-split` | Symlink |
| 3 | `config/keybinds/active.conf` | Update M-v and M-s bindings |
