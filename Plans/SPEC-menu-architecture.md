# SPEC: Menu Architecture — Global / Profile / Workspace
> Ready to execute. All file paths verified. No research needed.

---

## DISCOVERY: What already exists

The menu system is **further along than expected**. Do NOT rebuild from scratch.

### Already working
- `modules/menu/bin/nexus-menu` — shell launcher → `modules/menu/lib/core/menu_engine.py`
- `menu_engine.py` has a full **cascading layer system** at `get_list_layers(context)`:
  - `global:` → `modules/menu/lists/`
  - `profile:` → `~/.nexus/profiles/<active_profile>/lists/`
  - `workspace:` → `$PROJECT_ROOT/.nexus/lists/`
  - `system:` → `core/engine/lists/`
  - No prefix → merges ALL layers (cascading override)
- `render_home()` at line 116 — renders the top-level home menu
- `render_global_tabs()` at line 206 — renders tab switcher

### Already-wired keybinds (in `config/keybinds/active.conf`)
```
M-n   → nexus-menu --context system:modules:all    (new tab/launcher)
M-t   → nexus-menu --context local_stack           (tab switcher in stack)
M-T   → same as M-t
```

### What's MISSING
1. Top-level home menu does NOT have explicit Global/Profile/Workspace sections
2. No `--context global` / `--context profile` / `--context workspace` top-level items
3. Alt-p (Command Palette) not wired
4. Alt-m currently points to wrong binary (see SPEC-keybinds)

---

## WHAT TO BUILD

### Task 1: Add Global/Profile/Workspace sections to render_home()

**File:** `modules/menu/lib/core/menu_engine.py`
**Function:** `render_home()` — starts at line 116

Current `render_home()` loads from `home.yaml` files across layers. Extend it to emit
three explicit top-level entries that drill into scoped contexts:

```python
# Add to render_home() after existing home items:
items += [
    fmt("⬡  Global", "CONTEXT", "global:", section="Global"),
    fmt("◈  Profile", "CONTEXT", "profile:", section="Profile"),
    fmt("⬢  Workspace", "CONTEXT", "workspace:", section="Workspace"),
]
```

The `CONTEXT` type already triggers drill-down in the picker (see `resolve_sources()`).

### Task 2: Create YAML list definitions for each layer

**Create these directories and `_list.yaml` files:**

#### Global layer (`modules/menu/lists/`)
Already has: `agents/`, `boot/`, `build/`, `launch/`, `models/`, `notes/`, `scripts/`, `sessions/`, `settings/`, `shelf/`, `system/`, `vision/`

Add a top-level `_list.yaml` for the global context:
```yaml
# modules/menu/lists/_list.yaml
title: "Global"
description: "System-wide tools and capabilities"
icon: "⬡"
```

#### Profile layer (`~/.nexus/lists/`)
This is user-specific. Create the structure during first run. Add `onboarding.sh` to create:
```
~/.nexus/lists/
  _list.yaml      ← title: "Profile", description: "Your personal tools"
  tools/          ← user's preferred tools
  shortcuts/      ← custom shortcuts
```

#### Workspace layer (`$PROJECT_ROOT/.nexus/lists/`)
Project-specific. The `.nexus/` dir already exists. Add:
```
.nexus/lists/
  _list.yaml      ← title: "Workspace", description: "Project-specific"
  actions/        ← project scripts
  docs/           ← project docs
  compositions/   ← layout presets
```

### Task 3: Alt-n submenu → "New Tab" context

**Current binding** (already correct):
```
M-n  → nexus-menu --context system:modules:all
```

This shows ALL capabilities. Samir wants a "New Tab" submenu. The context is correct —
just rename the header in the YAML list:

**File:** `core/engine/lists/modules/all/_list.yaml` (create if missing)
```yaml
title: "New Tab"
description: "Open something new"
```

### Task 4: Alt-t → Tab switcher in current stack

**Current binding** (already correct):
```
M-t  → nexus-menu --context local_stack
```

`local_stack` is handled by `render_global_tabs()` at line 206. This is working.
If Samir says it's not working correctly, check that `render_global_tabs()` calls
`fmt()` for each active stack tab via the `stack list local` binary output.

---

## HOW THE CONTEXT/DRILL-DOWN WORKS

When a user selects an item with `type="CONTEXT"`, `menu_engine.py` recursively re-runs
with that context. The mechanism is in `resolve_sources()` at line 325.

Flow:
```
User opens menu → render_home() → selects "Workspace" →
  get_list_layers("workspace:") → PROJECT_ROOT/.nexus/lists/ →
  load all YAML files there → render them → user selects item →
    if item is also CONTEXT → drill down again
    if item is ROLE/NOTE/ACTION/etc → dispatch via nexus-ctl
```

---

## TESTING

After implementing, test with:
```bash
# Test global context
NEXUS_HOME=$(pwd) PROJECT_ROOT=$(pwd) .venv/bin/python3 \
  modules/menu/lib/core/menu_engine.py --context global:

# Test workspace context
NEXUS_HOME=$(pwd) PROJECT_ROOT=$(pwd) .venv/bin/python3 \
  modules/menu/lib/core/menu_engine.py --context workspace:

# Test home (shows all 3 sections)
NEXUS_HOME=$(pwd) PROJECT_ROOT=$(pwd) .venv/bin/python3 \
  modules/menu/lib/core/menu_engine.py
```

---

## FILES TO MODIFY (in order)

| # | File | Change |
|---|------|--------|
| 1 | `modules/menu/lib/core/menu_engine.py:116` | Add Global/Profile/Workspace to render_home() |
| 2 | `modules/menu/lists/_list.yaml` | Create global layer metadata |
| 3 | `.nexus/lists/_list.yaml` | Create workspace layer metadata |
| 4 | `core/engine/lists/modules/all/_list.yaml` | Create "New Tab" header |

**Do NOT touch `config/keybinds/active.conf`** — M-t and M-n are already correct.
