# Nexus Shell: Strategic Direction — March 2026

## Context

Samir feels like the project is a mess because it started with one idea and the idea evolved. This is true — and it's visible in the architecture. The project is not actually a mess in quality, but it IS in **architectural adolescence**: two systems running simultaneously (legacy bash + mature Python engine) with the Python execution pipeline left as stubs while features keep advancing. The result feels incoherent.

This plan establishes where the project actually stands, names the root cause, and proposes a clear next phase.

---

## Honest State Assessment

### What's Production-Ready (Don't Touch)
| Component | Maturity | Notes |
|-----------|----------|-------|
| `capabilities/registry.py` | ✅ PRODUCTION | Clean, fallback chains, extensible |
| `capabilities/base.py` | ✅ PRODUCTION | Well-specified ABC interfaces |
| `capabilities/adapters/tmux.py` | ✅ PRODUCTION | Full contract, 20+ methods |
| `capabilities/adapters/menu/` | ✅ PRODUCTION | gum, fzf, textual all work |
| Tests (PBT + BATS) | ✅ PRODUCTION | P1-P5 invariants, portability |
| WorkspaceOrchestrator | 🟡 BETA | Feature-complete, monolithic (577 lines) |
| MenuEngine | 🟡 BETA | Feature-complete, 5-layer cascading (586 lines) |

### What's Broken / Stub (The Real Problem)
| Component | Reality | Impact |
|-----------|---------|--------|
| `orchestration/executor.py` | 37 lines, incomplete | No capability execution pipeline |
| `orchestration/planner.py` | 60 lines, has "TODO: more logic here" comment | No request → workflow conversion |
| `state/state_engine.py` | No versioning, no validation, fragile | Can't rely on persistent state |
| `api/intent_resolver.py` | Hardcoded cases, bare excepts | Not extensible |

### The Legacy Bash Zone (The Mess Feeling)
- **~51 bash scripts** still running core logic
- `core/kernel/exec/`: 24 files, 1760 LOC — 60% real logic, NO Python equivalent yet
- `core/kernel/boot/`: 18 files, 1955 LOC — the boot chain, partial Python equivalent
- `core/services/`: 9 files, 90% thin wrappers → can be deleted/consolidated
- `core/ui/hud/`: 10 files, 70% real logic — no Python daemon equivalent yet

Python capabilities exist. Bash scripts exist. They run in parallel without talking to each other clearly. That's the mess.

---

## Root Cause

**The execution pipeline is the missing link.**

The capabilities layer (bottom) and the menu/UI layer (top) are both mature. But the middle — the piece that takes user intent and routes it through capabilities — is stub code. Every time a user action needs to do something, bash scripts bypass the Python engine and call tmux directly. The Python engine is real, but it's not in the loop.

```
User → Menu (works) → Intent Resolver → Planner → Executor → Capabilities
                           ↑                ↑           ↑
                      hardcoded         stub       stub/37 lines
```

---

## The Strategic Approach: "Engine First"

### Why Not Feature-First?
Phase 5.5 (Sovereign UX) and Phase 6.5 (AI Control Surface) are both blocked by the same problem: there's no clean request flow from user action → Python capability. Building more features on top of bash scripts creates more debt, not less.

### The Three-Phase Plan

---

### Phase 1: Close the Loop (~1-2 sessions)
**Goal:** Make the Python execution pipeline functional end-to-end.

**What to build:**
1. **Complete `executor.py`** — Make ExecutionCoordinator actually route through capabilities (it currently only handles EDIT and EXECUTE with bare logic)
2. **Complete `planner.py`** — Implement the 5 OpTypes (EDIT, EXPLORE, EXECUTE, RENDER, WAIT) so any intent can be converted to a workflow
3. **Harden `intent_resolver.py`** — Replace hardcoded cases with a registry-based dispatch mechanism; remove bare excepts
4. **State Engine versioning** — Add schema version + migration, stop fragile auto-type conversion

**Success criterion:** A user action from the menu successfully routes through `intent_resolver → planner → executor → tmux.py` without touching any bash script.

**What NOT to do:** Don't touch the bash scripts yet. Don't refactor workspace.py. Just close the loop.

---

### Phase 2: Unify the Interface (~2-3 sessions)
**Goal:** One entry point (`nxs` / `nexus-ctl`) that routes everything through the Python engine.

**What to build:**
1. **`nexus-ctl` CLI** — A Python CLI that receives all user commands and dispatches to the engine. The bash scripts become thin shells that call `nexus-ctl` instead of calling tmux directly.
2. **Delete dead bash wrappers** — `core/services/actions/` (5 ultra-thin files), `core/services/commands/profile.sh` & `workspace.sh` (pure dispatch)
3. **Port highest-value scripts** — `stack_manager.sh` and `switcher.sh` (the context navigation layer) are the highest-value targets; they're complex logic with no Python equivalent

**Success criterion:** `nxs` is the single entry point. Bash scripts either call `nexus-ctl` or are deleted.

---

### Phase 3: Advance Features (ongoing)
**Goal:** Resume roadmap progress from a clean foundation.

**Priority order (based on roadmap):**
1. **Phase 5.5 Sovereign UX** — Master Switcher (`Alt-m`), Command Palette (`Alt-p`), Quantum Splits — these are user-facing wins that build on the unified interface
2. **Phase 5.7 Pane Telemetry** — Event Bus → HUD Bridge; cross-pane event wiring
3. **Phase 6.5 AI Control Surface** — Agent Slot + LiteLLM proxy; builds on both telemetry and unified interface

---

## What to Work On First (Today)

**Option A: Start Phase 1 — Complete the Execution Pipeline**
- Complete `executor.py` and `planner.py`
- Build the actual Intent → Plan → Execute flow
- Duration: ~1 session
- Result: Python engine is fully functional end-to-end

**Option B: Audit & Delete First**
- Map exactly what's dead vs alive in the bash zone
- Delete obvious dead code first (clean the workspace visually)
- Duration: ~1 hour
- Result: The mess looks smaller immediately

**Option C: Feature Work (Phase 5.5)**
- Jump straight to Master Switcher or Command Palette
- Ignore the architecture debt for now
- Risk: More bash scripts will be written to support it

**My recommendation: Option A.** The execution pipeline is what makes the project coherent. Once that loop is closed, everything else is clearly positioned.

---

## Files to Modify in Phase 1

| File | Change |
|------|--------|
| `core/engine/orchestration/executor.py` | Complete ExecutionCoordinator (37 lines → ~150 lines) |
| `core/engine/orchestration/planner.py` | Implement all 5 OpTypes (60 lines → ~200 lines) |
| `core/engine/api/intent_resolver.py` | Registry-based dispatch, proper error handling |
| `core/engine/state/state_engine.py` | Add schema version field, remove fragile auto-conversion |

## Files to Leave Alone
- `core/engine/capabilities/` — PRODUCTION, don't touch
- `core/engine/orchestration/workspace.py` — BETA, works, refactor separately
- `core/services/internal/` — Daemon logic, leave for Phase 2
- All bash boot scripts — Leave for Phase 2

---

## Verification for Phase 1

1. Trace a user menu selection all the way through: `menu → intent_resolver → planner → executor → tmux.py.create_pane()`
2. Run existing PBT test suite — all P1-P5 invariants pass
3. Run `portability.bats` — no regressions
4. Check `state_engine.py` handles missing/malformed state gracefully

