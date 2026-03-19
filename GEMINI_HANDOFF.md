# Nexus Shell — Gemini Handoff Document
> Generated: 2026-03-19. Claude hit usage limit. You are continuing this work.

---

## WHO YOU ARE TALKING TO

**User: Samir** — senior engineer, opinionated, fast-moving. He does NOT want:
- Summaries of what you just did ("I've updated the file to...")
- Unsolicited refactors beyond what was asked
- Hesitation on clear tasks — just do it
- Emojis unless he asks

He DOES want:
- Concise, direct responses
- Ask before destructive actions (deleting files, force-push)
- Test before claiming something works
- Use the PAI Algorithm format (he has a hook that enforces it, just follow it)

---

## PROJECT: nexus-shell

A **meta-IDE** that orchestrates terminal tools (nvim, yazi, fzf, opencode) inside tmux, managed by a Python engine with a persistent daemon.

**Project root:** `/Users/Shared/Projects/nexus-shell`
**Python venv:** `.venv/bin/python`
**Run tests:** `.venv/bin/python -m pytest tests/unit/ --ignore=tests/unit/test_orchestrator_pbt.py --ignore=tests/unit/test_registry_properties.py -q`

---

## CURRENT STATE (as of last session)

### What was just completed
1. **Phase 1 — Execution pipeline** (`fd04a53`): executor.py, planner.py, nexus_ctl.py, switcher.py, state_engine.py, intent_resolver.py all implemented
2. **Phase 2 — Unified CLI** (`fd04a53`): `bin/nexus-ctl`, `bin/nxs-switch` symlinks; 5 dead bash wrappers deleted; `core/kernel/exec/router.sh` reduced from 78→14 lines
3. **Momentum layout fix** (`ad560fc`): Saved tmux layouts now restore correctly on boot. Key insight: `client-session-changed` hook never fires on initial attach. Fix: write remapped layout to `/tmp/nexus_<user>/momentum_layout.sh`, then `bin/nxs` (symlink to `core/kernel/boot/launcher.sh`) spawns a background process that applies it 0.5s after `tmux attach-session`.
4. **124 unit tests** (`82a6107`): Full coverage of executor, planner, state_engine, nexus_ctl, switcher

### Tests: all passing
```
145 passed in 7.82s
```

---

## ARCHITECTURE — KEY FILES

### Boot flow
```
bin/nxs → core/kernel/boot/launcher.sh
  → core/engine/lib/daemon_client.py  boot_layout
    → core/services/internal/daemon.py  (persistent Python process)
      → core/engine/orchestration/workspace.py  apply_composition()
        → _build()            # fresh composition from JSON
        → _build_momentum()   # restore from saved session state
```

### Engine layers
```
core/engine/api/
  nexus_ctl.py        — unified CLI entry point (bin/nexus-ctl)
  intent_resolver.py  — maps TYPE|PAYLOAD → plan dict
  switcher.py         — context-aware Alt-m fuzzy switcher (bin/nxs-switch)

core/engine/orchestration/
  workspace.py        — WorkspaceOrchestrator: builds tmux layouts
  executor.py         — ExecutionCoordinator: runs plans through capabilities
  planner.py          — WorkflowPlanner: converts intents to ExecutionPlan

core/engine/capabilities/
  registry.py         — CapabilityRegistry, REGISTRY singleton
  base.py             — ABCs: EditorCapability, ExplorerCapability, MultiplexerCapability...
  adapters/
    multiplexer/tmux.py   — TmuxAdapter (20+ methods)
    multiplexer/null.py   — NullAdapter for tests
    editor/neovim.py
    explorer/yazi.py
    menu/gum_menu.py, fzf_menu.py, textual_menu.py

core/engine/state/
  state_engine.py     — NexusStateEngine: JSON state with dual-fallback persistence

core/kernel/
  layout/save_layout.py   — captures live tmux layout to state.json
  boot/launcher.sh        — main boot script (bin/nxs)
  boot/pane_wrapper.sh    — wraps commands launched in panes
  stack/stack             — compiled Go binary: manages stack identities
```

### State file
`.nexus/state.json` — project-local state. Contains:
- `session.windows.{idx}.layout_string` — saved tmux layout string
- `session.windows.{idx}.panes[]` — pane metadata (id, command, geom percentages)
- `ui.slots.{name}.tool` — tool assigned to each slot

### Compositions
`core/ui/compositions/*.json` — JSON layout definitions. Example: `vscodelike.json`
```json
{"layout": {"type": "hsplit", "panes": [
  {"id": "files", "size": 30, "command": "$NEXUS_FILES"},
  {"type": "vsplit", "panes": [
    {"id": "menu", "size": "8", "command": "..."},
    {"id": "editor", "command": "$EDITOR_CMD"},
    {"id": "terminal", "size": "10", "command": "/bin/zsh -i"}
  ]},
  {"id": "chat", "size": 45, "command": "/bin/zsh -i"}
]}}
```

---

## WHAT'S NEXT — SAMIR'S REQUESTS (in priority order)

### 1. Menu Architecture (HIGH PRIORITY)
Samir wants a structured menu system with:
- **Three submenu levels**: global / profile / workspace
- Each submenu has its own sub-submenus
- **Alt-t**: switch to tab in a stack (tab within a pane)
- **Alt-n**: new tab submenu

Current menu entry point: `core/engine/api/nexus_ctl.py` + `intent_resolver.py`
The menu binary is: `modules/menu/bin/nexus-menu` (check if this exists)
Existing menu adapters: `core/engine/capabilities/adapters/menu/` (gum, fzf, textual)

The menu should be driven by the capability layer — not hardcoded bash. The `_registry.get_best(CapabilityType.MENU)` pattern is already in place.

**Questions to answer before building:**
- Does `modules/menu/bin/nexus-menu` exist? Read it.
- What does the current menu look like? Check `core/ui/hud/` and existing menu compositions
- How do global/profile/workspace map to the existing intent types?

### 2. Phase 3 Features (MEDIUM PRIORITY)
From `Plans/drifting-moseying-quokka.md`:
- **Master Switcher (Alt-m)**: `switcher.py` is already written, needs keybind wiring
- **Command Palette (Alt-p)**: not yet built
- **Quantum Splits**: not yet built

### 3. Port stack_manager.sh (LOW PRIORITY)
`core/kernel/exec/stack_manager.sh` (263 lines) — no Python equivalent yet. Deferred.

---

## HOW TO CONTINUE

### Running nexus
```bash
bin/nxs                    # boot with saved session
bin/nxs vscodelike         # boot with fresh vscodelike layout
pkill -f daemon.py         # kill daemon (required after code changes)
```

### Daemon logs
```bash
cat /tmp/nexus_samir/daemon.log | tail -50
```

### Running tests
```bash
.venv/bin/python -m pytest tests/unit/ \
  --ignore=tests/unit/test_orchestrator_pbt.py \
  --ignore=tests/unit/test_registry_properties.py -v
```

### Using Gemini CLI as a sub-agent (IT WORKS!)
```bash
gemini -p "Your prompt here" 2>/dev/null
```
Gemini CLI is at `~/.npm-global/bin/gemini` v0.34.0. Use it for:
- Code review: `gemini -p "Review this code: $(cat file.py)"`
- Research: parallel with other work
- Second opinion on architecture decisions

---

## STRATEGIC CONTEXT

The project went through 3 phases:
1. **Phase 1** ✅: Complete execution pipeline (executor → planner → capabilities)
2. **Phase 2** ✅: Unified interface (nexus-ctl CLI, delete dead bash wrappers)
3. **Phase 3** 🔄 IN PROGRESS: Sovereign UX (menu architecture, Alt-m/p, Quantum Splits)

The architecture is **Engine First** — capabilities layer (bottom) and menu/UI layer (top) are mature. The execution pipeline (middle) is now complete. New features should go through `nexus_ctl → intent_resolver → planner → executor → capabilities`.

**Do NOT** bypass the Python engine to call tmux directly in new bash scripts. That's the pattern being replaced.

---

## IMPORTANT QUIRKS

1. **Daemon must be restarted** after any Python file changes: `pkill -f daemon.py && bin/nxs`
2. **bin/nxs is a symlink** to `core/kernel/boot/launcher.sh` — edit the `.sh`, not the symlink
3. **REGISTRY is a module-level singleton** in `core/engine/capabilities/registry.py` — mock it with `patch("engine.orchestration.executor.REGISTRY")` in tests
4. **TmuxAdapter import path quirk**: imported as `from engine.capabilities.adapters.tmux import TmuxAdapter` but file is at `adapters/multiplexer/tmux.py` — there's a `__init__.py` re-export somewhere
5. **Hypothesis tests** (`test_orchestrator_pbt.py`, `test_registry_properties.py`) need `hypothesis` package — skip with `--ignore` flag
6. **3x duplicate log lines** in daemon.log — cosmetic bug, `log()` writes to stdout + stderr + file

---

## GIT STATE
Branch: `main`
Last 3 commits:
- `82a6107` test(engine): 124 unit tests
- `ad560fc` fix(momentum): layout post-attach background process
- `fd04a53` refactor(engine): execution pipeline + unified CLI

**Do NOT push** without Samir confirming.
