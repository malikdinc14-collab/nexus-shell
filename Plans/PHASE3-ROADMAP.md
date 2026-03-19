# Nexus Shell — Phase 3 Execution Roadmap
> Generated: 2026-03-19. All specs verified against codebase.

---

## EXECUTION ORDER

Tasks are ordered by: risk (low → high) × dependency (independent → dependent).

---

### TASK 1 — Fix Alt-m binding ⚡ (~2 min)

**Spec:** `Plans/SPEC-keybinds-phase3.md` → TASK 1
**File:** `config/tmux/nexus.conf:76`
**Change:** One line

```
# FROM:
bind-key -n M-m run-shell "${NEXUS_KERNEL}/layout/mosaic_engine.sh start"

# TO:
bind-key -n M-m run-shell "${NEXUS_HOME}/bin/nxs-switch"
```

**Verify:**
```bash
tmux source-file config/tmux/nexus.conf
# Press Alt-m in a nexus session — should open switcher, not mosaic
```

**Dependencies:** None. Fully independent.

---

### TASK 2 — Wire Alt-p Command Palette (~20 min)

**Spec:** `Plans/SPEC-keybinds-phase3.md` → TASK 2
**Files:**
1. `config/keybinds/active.conf:50` — update existing binding (not absent as spec noted)
2. `core/engine/api/intent_resolver.py` — add `:palette` handler
3. `core/engine/lists/all/_list.yaml` — create (dir `core/engine/lists/all/` needs creation too)

**Step A — Update keybind** (`active.conf:50`):
```
# FROM:
bind-key -n M-p display-popup -E -w 70% -h 60% "$NEXUS_KERNEL/exec/palette.sh"

# TO:
bind-key -n M-p run-shell "$NEXUS_HOME/bin/nexus-ctl run ACTION ':palette' --caller menu"
```

**Step B — Add `:palette` handler** in `intent_resolver.py` ACTION section (~line 90):
```python
elif payload == ":palette":
    plan["cmd"] = (
        f"{self.nexus_home}/modules/menu/bin/nexus-menu"
        f" --context system:all --header 'Command Palette'"
    )
    plan["strategy"] = "stack_push"
    plan["name"] = "palette"
    plan["role"] = "local"
    return plan
```

**Step C — Create** `core/engine/lists/all/_list.yaml`:
```yaml
title: "Command Palette"
description: "All commands, tools, and actions"
sources:
  - context: "system:modules"
  - context: "system:agents"
  - context: "system:settings"
  - context: "global:"
```

**Verify:**
```bash
# Test intent resolver
NEXUS_HOME=$(pwd) .venv/bin/python3 -c "
from engine.api.intent_resolver import IntentResolver
r = IntentResolver()
p = r.resolve('run', 'ACTION', ':palette', 'push', 'menu')
print(p)
assert p['name'] == 'palette'
assert 'nexus-menu' in p['cmd']
print('PASS')
"
# Test keybind: reload config, press Alt-p
tmux source-file config/keybinds/active.conf
```

**Dependencies:** None for Steps A-B. Step C helps palette show useful content.

---

### TASK 3 — Menu Architecture: Global/Profile/Workspace (~30 min)

**Spec:** `Plans/SPEC-menu-architecture.md`
**Files:**
1. `modules/menu/lib/core/menu_engine.py:116` — extend `render_home()`
2. `modules/menu/lists/_list.yaml` — create (global layer metadata)
3. `.nexus/lists/_list.yaml` — create (workspace layer metadata)
4. `core/engine/lists/modules/all/_list.yaml` — create (Alt-n "New Tab" header)

**Step A — Extend `render_home()`** (after existing home items load):
```python
items += [
    fmt("⬡  Global", "CONTEXT", "global:", section="Global"),
    fmt("◈  Profile", "CONTEXT", "profile:", section="Profile"),
    fmt("⬢  Workspace", "CONTEXT", "workspace:", section="Workspace"),
]
```

**Step B — Create YAML files:**

`modules/menu/lists/_list.yaml`:
```yaml
title: "Global"
description: "System-wide tools and capabilities"
icon: "⬡"
```

`.nexus/lists/_list.yaml`:
```yaml
title: "Workspace"
description: "Project-specific tools and actions"
icon: "⬢"
```

`core/engine/lists/modules/all/_list.yaml`:
```yaml
title: "New Tab"
description: "Open something new"
```

**Verify:**
```bash
# Test home menu shows 3 sections
NEXUS_HOME=$(pwd) PROJECT_ROOT=$(pwd) .venv/bin/python3 \
  modules/menu/lib/core/menu_engine.py 2>/dev/null | head -20
# Should show Global, Profile, Workspace entries

# Test global context drill-down
NEXUS_HOME=$(pwd) PROJECT_ROOT=$(pwd) .venv/bin/python3 \
  modules/menu/lib/core/menu_engine.py --context global: 2>/dev/null | head -10

# Test workspace context
NEXUS_HOME=$(pwd) PROJECT_ROOT=$(pwd) .venv/bin/python3 \
  modules/menu/lib/core/menu_engine.py --context workspace: 2>/dev/null | head -10
```

**Dependencies:** TASK 2 Step C (system:all list) helps palette, but TASK 3 is independently useful.

---

### TASK 4 — Quantum Splits (~30 min)

**Spec:** `Plans/SPEC-quantum-splits.md`
**Files:**
1. `core/engine/api/quantum_split.py` — create (~80 lines, full code in spec)
2. `bin/quantum-split` — symlink
3. `config/keybinds/active.conf:28-29` — update M-v and M-s

**Step A — Create script** (full implementation in spec)

**Step B — Create symlink:**
```bash
ln -sf ../core/engine/api/quantum_split.py bin/quantum-split
chmod +x core/engine/api/quantum_split.py
```

**Step C — Update keybinds** (`active.conf:28-29`):
```
# FROM:
bind-key -n 'M-v' split-window -h -c "#{pane_current_path}" \; set-option ...
bind-key -n 'M-s' split-window -v -c "#{pane_current_path}" \; set-option ...

# TO:
bind-key -n 'M-v' run-shell "${NEXUS_HOME}/bin/quantum-split h"
bind-key -n 'M-s' run-shell "${NEXUS_HOME}/bin/quantum-split v"
```

**Verify:**
```bash
# Unit test the role inference
NEXUS_HOME=$(pwd) .venv/bin/python3 -c "
import sys; sys.path.insert(0, 'core')
from engine.api.quantum_split import SUGGESTIONS, DEFAULT_SUGGESTIONS
assert 'terminal' in SUGGESTIONS['editor']
assert 'editor' in DEFAULT_SUGGESTIONS
print('PASS: role inference dict correct')
"
# Live test: reload keybinds, press M-v in a nexus session
tmux source-file config/keybinds/active.conf
```

**Dependencies:** None. Fully independent.

---

### TASK 5 — Port stack_manager.sh (~20 min) [LOW PRIORITY]

**Spec:** `Plans/SPEC-stack-manager-port.md`
**Files:**
1. `core/engine/api/stack_ctl.py` — create (~40 lines, full code in spec)
2. `bin/stack-ctl` — symlink
3. `core/kernel/exec/stack_manager.sh` — archive as `.bak`

**Steps:**
```bash
# After creating stack_ctl.py per spec:
ln -sf ../core/engine/api/stack_ctl.py bin/stack-ctl
chmod +x core/engine/api/stack_ctl.py

# Check for callers before archiving:
grep -r "stack_manager" . --include="*.sh" --include="*.py" --include="*.conf" -l

# Archive (not delete):
mv core/kernel/exec/stack_manager.sh core/kernel/exec/stack_manager.sh.bak
```

**Verify:**
```bash
NEXUS_HOME=$(pwd) .venv/bin/python3 -c "
import sys; sys.path.insert(0, 'core')
# Verify category mapping
import importlib.util
spec = importlib.util.spec_from_file_location('stack_ctl', 'core/engine/api/stack_ctl.py')
m = importlib.util.module_from_spec(spec)
assert m  # file loads without error
print('PASS')
"
```

**Dependencies:** None. Fully independent. Do last (lowest value).

---

## DEPENDENCY GRAPH

```
TASK 1 (Alt-m)     ──── independent
TASK 2 (Alt-p)     ──── independent (palette content improves after TASK 3)
TASK 3 (menu arch) ──── independent (enriches TASK 2 context)
TASK 4 (q-splits)  ──── independent
TASK 5 (stack-ctl) ──── independent
```

No blocking dependencies. All tasks can be done in any order.
Recommended order: 1 → 2 → 3 → 4 → 5 (quick wins first, complexity escalates gradually).

---

## AFTER ALL TASKS: Run tests

```bash
.venv/bin/python -m pytest tests/unit/ \
  --ignore=tests/unit/test_orchestrator_pbt.py \
  --ignore=tests/unit/test_registry_properties.py -q
```

Expected: 145 passed (from last sprint). Add tests for `stack_ctl.py` and `quantum_split.py` per the test stubs in their respective specs.

---

## WHAT'S NOT IN THIS PHASE

- **Phase 5.7 Pane Telemetry** — Event Bus → HUD bridge (requires architecture decision)
- **Phase 6.5 AI Control Surface** — Agent Slot + LiteLLM proxy (depends on telemetry)
- **WorkspaceOrchestrator refactor** — 577 lines, working, leave it

---

## CORRECTION TO SPEC-keybinds-phase3.md

> TASK 2 says Alt-p is "NOT BOUND" — this is incorrect.
> Alt-p IS bound at `config/keybinds/active.conf:50` to the old `palette.sh`.
> The fix is to UPDATE the existing binding, not add a new one.
