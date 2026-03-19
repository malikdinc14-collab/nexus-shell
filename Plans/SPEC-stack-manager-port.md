# SPEC: Port stack_manager.sh to Python
> Ready to execute. stack_manager.sh is at core/kernel/exec/stack_manager.sh (263 lines)

---

## VERDICT: Mostly already done

`stack_manager.sh` is largely superseded by the existing Python system.
The "port" is mostly **deletion + thin wiring**, not a rewrite.

### What stack_manager.sh does vs what already exists

| Category | stack_manager.sh | Python equivalent |
|----------|-----------------|-------------------|
| `roles` | fzf picker of editor/files/chat/menu/terminal | `nexus-ctl run ROLE <name>` via `intent_resolver.py` |
| `chat/editor/files/terminal/menu` (TOOL type) | fzf of tools from user_stacks.yaml | `menu_engine.py --context <role>` |
| `models` | fzf of AI models | `nexus-ctl run MODEL <name>` |
| `docs/notes/specs` | find + fzf on directory | `menu_engine.py --context notes` (already in lists/) |
| `config/settings` | fzf of config files | `menu_engine.py --context system:settings` |
| `actions/build` | find scripts in .nexus/actions | `menu_engine.py --context workspace:actions` |
| drill-down via Alt-E | bash fzf become() | menu_engine.py CONTEXT type triggers recursion |

**Conclusion: No new logic needed.** The port = replacing bash callers with `nexus-ctl` calls.

---

## ACTUAL WORK NEEDED

### 1. Create a Python CLI wrapper (`core/engine/api/stack_ctl.py`)

This replaces `stack_manager.sh` as the entry point. ~40 lines:

```python
#!/usr/bin/env python3
# core/engine/api/stack_ctl.py
"""
Replaces core/kernel/exec/stack_manager.sh
Usage: stack-ctl <category> [query]
  Categories: roles, models, docs, notes, actions, config, chat, editor
"""
import os, sys, subprocess
from pathlib import Path

NEXUS_HOME = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[3]))
MENU_BIN = NEXUS_HOME / "modules/menu/bin/nexus-menu"

CATEGORY_TO_CONTEXT = {
    "roles":    "system:modules",
    "models":   "system:models",
    "docs":     "notes",           # global: notes layer
    "notes":    "notes",
    "specs":    "workspace:specs",
    "actions":  "workspace:actions",
    "config":   "system:settings",
    "settings": "system:settings",
    "chat":     "chat",
    "editor":   "editor",
    "files":    "files",
    "terminal": "terminal",
}

def main():
    category = sys.argv[1] if len(sys.argv) > 1 else "roles"
    query = sys.argv[2] if len(sys.argv) > 2 else ""
    context = CATEGORY_TO_CONTEXT.get(category, f"workspace:{category}")
    cmd = [str(MENU_BIN), "--context", context]
    if query:
        cmd += ["--query", query]
    os.execv(str(MENU_BIN), cmd)

if __name__ == "__main__":
    main()
```

### 2. Add symlink
```bash
ln -sf ../core/engine/api/stack_ctl.py bin/stack-ctl
chmod +x core/engine/api/stack_ctl.py
```

### 3. Update any callers of stack_manager.sh

Search for callers:
```bash
grep -r "stack_manager" . --include="*.sh" --include="*.py" --include="*.conf" -l
```

Replace with `nexus-ctl` or `stack-ctl` as appropriate.

### 4. Archive (don't delete yet)
```bash
mv core/kernel/exec/stack_manager.sh core/kernel/exec/stack_manager.sh.bak
```

---

## FILES TO CREATE/MODIFY

| # | File | Action |
|---|------|--------|
| 1 | `core/engine/api/stack_ctl.py` | Create (40 lines) |
| 2 | `bin/stack-ctl` | Symlink |
| 3 | `core/kernel/exec/stack_manager.sh` | Archive as .bak after verifying no active callers |

---

## TESTS TO ADD

```python
# tests/unit/test_stack_ctl.py
def test_category_to_context_mapping():
    # roles → system:modules
    # notes → notes
    # unknown → workspace:<category>
    pass

def test_execv_called_with_correct_args():
    # mock os.execv, verify correct context passed
    pass
```
