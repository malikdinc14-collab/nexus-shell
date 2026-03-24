# Plan: nexus-shell — Complete Remaining Implementation

## Context

Previous session agents built ~8,000 lines across 36 Python modules, 7 shell scripts, and 36 test files before hitting a rate limit. Code is uncommitted but production-quality. Three stubs remain, keymap wiring needs end-to-end testing, and Command Graph needs live source integration. Goal: complete all remaining work in one session.

## Execution Order

### 1. Run tests to establish baseline
- `python -m pytest tests/ -v` to see what passes/fails
- Prioritize fixing any broken tests before adding new code

### 2. Fill the three stubs

**2a. Live source resolvers** (`core/engine/graph/live_sources.py`)
- 10 async resolver functions currently return placeholder strings
- Implement real resolvers using subprocess: git branch, open ports, running processes, active packs, tmux sessions, etc.
- Pattern: `asyncio.create_subprocess_exec` → parse stdout → return formatted string

**2b. Workspace save/restore** (`core/engine/api/workspace_handler.py`)
- Wire `handle_save()` and `handle_restore()` into existing `core/engine/momentum/session.py`
- session.py already has complete save/restore logic — just need to call it

**2c. Neovim buffer introspection** (`core/engine/capabilities/adapters/editor/neovim.py`)
- Implement `get_current_buffer()` via `nvim --server {socket} --remote-expr 'expand("%:p")'`
- Find nvim socket from `$NVIM` env var or scan `/tmp/nvim*/`

### 3. End-to-end keymap wiring
- Verify `config/tmux/nexus.conf` Alt+ bindings → `bin/ui/*.sh` scripts → `nexus-ctl` → handlers
- Test flow: Alt+m → menu-popup.sh → nexus_ctl menu show → menu_handler → fzf/gum display
- Test flow: Alt+n → stack-push.sh → nexus_ctl stack push → stack_handler → new tab
- Fix any broken pipes in the chain

### 4. Command Graph live integration
- Wire live source resolvers into `core/engine/graph/loader.py` menu rendering
- Make `menu_handler.py` call live source resolution before rendering nodes
- Test: menu shows real git branch, real open ports, real process list

### 5. Fix any remaining test failures
- Run full suite again after changes
- Add tests for new live source implementations

## Key Files to Modify

| File | Change |
|------|--------|
| `core/engine/graph/live_sources.py` | Replace 10 stub resolvers with real implementations |
| `core/engine/api/workspace_handler.py` | Wire save/restore to momentum/session.py |
| `core/engine/capabilities/adapters/editor/neovim.py` | Implement get_current_buffer() |
| `core/engine/api/menu_handler.py` | Wire live source resolution into menu rendering |
| `config/tmux/nexus.conf` | Fix any broken keybinding paths |
| `bin/ui/*.sh` | Fix any broken script paths or argument handling |

## Key Files to Reuse (already complete)

| File | What it provides |
|------|-----------------|
| `core/engine/momentum/session.py` | Full save/restore orchestration |
| `core/engine/momentum/geometry.py` | Proportional pane geometry |
| `core/engine/momentum/stack_persistence.py` | Tab stack serialization |
| `core/engine/graph/resolver.py` | Multi-layer scope merging |
| `core/engine/graph/node.py` | CommandGraphNode with 4 node types |
| `core/engine/bus/enhanced_bus.py` | Event pub/sub for wiring |
| `core/engine/stacks/manager.py` | StackManager singleton |

## Verification

1. `python -m pytest tests/ -v` — all 36 test files pass
2. `python -m core.engine.cli.nexus_ctl menu show` — CLI outputs menu JSON
3. `python -m core.engine.cli.nexus_ctl stack list` — shows tab stacks
4. Manual in tmux: `tmux source config/tmux/nexus.conf` → Alt+m opens menu
5. Grep for "pending"/"placeholder"/"stub" — no remaining stubs in core/
