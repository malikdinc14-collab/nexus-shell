# SPEC: Phase 3 Keybind Wiring — Alt-m, Alt-p, Alt-t, Alt-n
> Ready to execute. All file paths verified.

---

## CURRENT STATE

All keybinds are in `config/keybinds/active.conf` (sourced by `config/tmux/nexus.conf`).

### What's broken/missing

| Key | Current target | Should be |
|-----|---------------|-----------|
| M-m | `mosaic_engine.sh start` (wrong!) | `bin/nxs-switch` (Python switcher) |
| M-p | **NOT BOUND** | Command Palette |
| M-t | `nexus-menu --context local_stack` ✅ | No change needed |
| M-n | `nexus-menu --context system:modules:all` ✅ | No change needed |

---

## TASK 1: Fix Alt-m — Wire Master Switcher

**File:** `config/tmux/nexus.conf`

Find line (currently reads):
```
bind-key -n M-m run-shell "${NEXUS_KERNEL}/layout/mosaic_engine.sh start"
```

Replace with:
```
bind-key -n M-m run-shell "${NEXUS_HOME}/bin/nxs-switch"
```

`bin/nxs-switch` is a symlink to `core/engine/api/switcher.py`. Already written. Already tested.

**switcher.py behavior:**
- In editor pane (title="editor") with nvim RPC → switch nvim tabs/buffers
- In terminal pane (title starts "term:" or ="terminal") → switch shell tabs
- Anywhere else → fuzzy switch tmux windows

**After change:** Reload tmux config:
```bash
tmux -L nexus_nexus-shell source-file config/tmux/nexus.conf
```

---

## TASK 2: Add Alt-p — Command Palette

**File:** `config/keybinds/active.conf`

Add after the M-n binding:
```
# --- Command Palette (Alt+P) ---
bind-key -n M-p run-shell "$NEXUS_HOME/bin/nexus-ctl run ACTION ':palette' --caller menu"
```

This triggers `intent_resolver.py` with a special `:palette` action. Add the handler:

**File:** `core/engine/api/intent_resolver.py`
**Method:** `resolve()`, in the ACTION section around line 90

Add before the generic `else`:
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

The palette shows ALL items from `system:` context — the full command space.

**Create the system:all YAML index:**
`core/engine/lists/all/_list.yaml`:
```yaml
title: "Command Palette"
description: "All commands, tools, and actions"
sources:
  - context: "system:modules"
  - context: "system:agents"
  - context: "system:settings"
  - context: "global:"
```

---

## TASK 3: Verify Alt-t stack tab switching

**Current binding:**
```
M-t  → stack push local "nexus-menu --context local_stack" "Active Stack"
```

This opens `nexus-menu` inside the stack. The `local_stack` context is rendered by
`render_global_tabs()` in `menu_engine.py:206`.

**If this isn't working**, the issue is likely that `render_global_tabs()` calls:
```python
subprocess.check_output([str(stack_bin), "list", "local"])
```
The `stack` binary at `core/kernel/stack/stack` must be compiled. Check:
```bash
ls -la core/kernel/stack/stack
file core/kernel/stack/stack
```

---

## APPLY ALL CHANGES

```bash
# After edits, reload tmux keybinds (no daemon restart needed)
tmux -L nexus_nexus-shell source-file "$NEXUS_HOME/config/tmux/nexus.conf"

# Or if session name is different:
tmux source-file config/tmux/nexus.conf
```

---

## TESTS TO ADD

Add to `tests/unit/test_intent_resolver.py`:
```python
def test_palette_action_dispatches_to_menu():
    resolver = IntentResolver()
    plan = resolver.resolve("run", "ACTION", ":palette", "push", "menu")
    assert plan["name"] == "palette"
    assert "nexus-menu" in plan["cmd"]
    assert "--context system:all" in plan["cmd"] or "palette" in plan["cmd"]
```
