# Operational Tasks: nexus-shell

## 1. Phase 1: Foundation & Config Cascade

Blocking prerequisites: data models, config architecture, CLI skeleton. Everything else depends on these.

- [ ] **T001: Create config directory structure**
  - **Description**: Create `~/.config/nexus/` global config scaffold (keymap.conf, theme.yaml, hud.yaml, adapters.yaml, connectors.yaml, profiles/, packs/, compositions/, actions/, menus/) and `.nexus/` workspace scaffold (workspace.yaml + same subdirs). Write defaults for each file per design Section 5.2.
  - **Traces to**: P-04, P-12 | R-27, R-30, R-32

- [ ] **T002: Implement scope cascade resolver**
  - **Description**: Build `core/engine/graph/resolver.py` with `resolve_config(key)` that reads workspace `.nexus/` → active profile → global `~/.config/nexus/` per design Section 5.3. Return first non-None value. Unit test with all three tiers and override scenarios.
  - **Traces to**: P-04 | R-27

- [ ] **T003: Extend AdapterManifest on all adapters**
  - **Description**: Add `AdapterManifest` dataclass (design Section 3.3) to `CapabilityRegistry`. Extend every existing adapter (Neovim, Yazi, tmux, fzf, gum, Textual, OpenCode, NullMultiplexer) with manifest declaring `native_multiplicity`, `priority`, `binary`, `is_available()`. Neovim sets `native_multiplicity=True`.
  - **Traces to**: P-01, P-02, P-13 | R-02, R-03, R-12

- [ ] **T004: Create NullMenuAdapter**
  - **Description**: Implement `NullMenuAdapter` (design Section 3.3) as a fallback menu renderer using simple numbered stdin selection. Register with priority 0 in CapabilityRegistry. Test that it activates when fzf/gum/Textual are all unavailable.
  - **Traces to**: P-13 | R-33

- [ ] **T005: Create nexus-ctl CLI skeleton**
  - **Description**: Build the `nexus-ctl` CLI entry point (design Section 4.2) with domain-based subcommands: `menu`, `capability`, `stack`, `tabs`, `pane`, `workspace`, `pack`, `profile`, `config`, `bus`. Each subcommand is a stub that prints "not implemented" for now. Wire as the single entry point for all keybinding handlers.
  - **Traces to**: P-10 | R-14

- [ ] **T006: Migrate profile loader to Python**
  - **Description**: Port `core/engine/env/profile_loader.sh` to Python `core/engine/profiles/manager.py`. Read profile YAML (design Section 3.5), apply composition, theme, HUD modules, keybind overrides, env vars. Integrate with scope cascade (T002). Preserve backward compat with existing profile YAMLs in `config/profiles/`.
  - **Traces to**: P-08 | R-45, R-46

---

## 2. Phase 2: Tab Stacks

The core navigation primitive. Panes become stacks; tools become tabs.

- [ ] **T010: Implement Tab and TabStack data models**
  - **Description**: Create `core/engine/stacks/stack.py` with `Tab`, `TabStack` dataclasses per design Section 3.2. Implement `push()`, `pop()`, `rotate()` methods with atomicity guarantees. Unit test all operations including edge cases (empty stack, single tab, wrap-around rotation).
  - **Traces to**: P-02, P-03 | R-05, R-06, R-07, R-08

- [ ] **T011: Implement TabReservoir**
  - **Description**: Create `core/engine/stacks/reservoir.py` with `TabReservoir` (design Section 3.2). `shelve()` detaches a tab from its pane (keeps alive in background). `recall()` pulls a tab from reservoir into a target pane. Unit test lifecycle.
  - **Traces to**: P-02 | R-09

- [ ] **T012: Implement StackManager**
  - **Description**: Create `core/engine/stacks/manager.py` — the runtime manager that tracks all TabStacks across all panes. Maps tmux pane IDs → TabStack instances. Handles creation of anonymous stacks on pane split (R-11), tab push/pop/rotate dispatch, and native multiplicity delegation (R-12). Publishes UI events (tab.pushed, tab.popped, tab.rotated) to event bus.
  - **Traces to**: P-02, P-03 | R-05, R-06, R-07, R-08, R-11, R-12

- [ ] **T013: Implement stack_handler.py (nexus-ctl stack)**
  - **Description**: Create `core/engine/api/stack_handler.py` — the handler for `nexus-ctl stack {push|pop|rotate}`. On `push`: create new anonymous tab in focused stack. On `pop`: kill active tab, reveal next; if last tab, show warning prompt (tmux confirm-before or fzf confirm) and offer destroy-pane or cancel. On `rotate +1/-1`: cycle through tabs. All operations go through StackManager (T012).
  - **Traces to**: P-03 | R-06, R-07, R-08

- [ ] **T014: Implement pane-border tab bar**
  - **Description**: Create `core/engine/stacks/tabbar.py` — generates the tmux `pane-border-format` string showing tab indicators (e.g., `[e] [c] [t]` with active highlighted). Configurable via `tabbar.yaml`: always / on-demand / off. Hook into tmux pane-border-format refresh on tab stack changes.
  - **Traces to**: P-02 | R-13

- [ ] **T015: Wire tmux pane events to StackManager**
  - **Description**: Use tmux hooks (`after-split-window`, `pane-focus-changed`, etc.) to notify StackManager of pane creation/destruction/focus changes. On split: create new anonymous TabStack. On pane destroy: clean up stack and move tabs to reservoir if configured.
  - **Traces to**: P-02 | R-05, R-11

---

## 3. Phase 3: Modeless Keymap

Wire every Alt+key binding through tmux → nexus-ctl → handler.

- [ ] **T020: Rewrite nexus.conf keybindings**
  - **Description**: Replace all existing keybindings in `config/tmux/nexus.conf` with the new modeless keymap (design Section 4.1). Every Alt+key runs `nexus-ctl <domain> <action>`. Remove stale bindings (e.g., Alt+m → mosaic_engine.sh). Keep Ctrl+Space and Alt+z (focus mode) as-is if they don't conflict.
  - **Traces to**: P-10 | R-14, R-15

- [ ] **T021: Implement pane_handler.py (nexus-ctl pane)**
  - **Description**: Create `core/engine/api/pane_handler.py` — handler for `nexus-ctl pane {kill|split-v|split-h}`. `kill`: destroy focused pane and all tabs in its stack (R-21). `split-v/split-h`: split pane, create new anonymous stack in the new container (R-22). Dispatch through StackManager.
  - **Traces to**: P-02 | R-21, R-22

- [ ] **T022: Implement tab_manager.py (nexus-ctl tabs)**
  - **Description**: Create `core/engine/api/tab_manager.py` — handler for `nexus-ctl tabs list`. Uses Menu capability to render a submenu of active tabs in the focused stack. Shows capability type, adapter name, role. Enter jumps to tab. Supports close-from-list.
  - **Traces to**: P-11 | R-20

- [ ] **T023: Implement keymap.conf loader**
  - **Description**: Build a loader in `core/engine/profiles/manager.py` that reads `keymap.conf` (global + workspace) and generates additional tmux `bind-key` commands at startup. Format: `Alt+F5 = nexus-ctl workspace save`. Merged via scope cascade. Applied on profile switch and config reload.
  - **Traces to**: P-10 | R-14

- [ ] **T024: End-to-end keymap integration test**
  - **Description**: BATS test that starts a tmux session with nexus.conf, verifies every Alt+key binding exists and routes to the correct `nexus-ctl` command. Not functional testing (that's per-handler) — just verifying the wiring is complete.
  - **Traces to**: P-10 | R-14, R-15

---

## 4. Phase 4: Command Graph

Node model, scope resolution, YAML loading, menu rendering, landing page.

- [ ] **T030: Implement CommandGraphNode data model**
  - **Description**: Create `core/engine/graph/node.py` with `CommandGraphNode`, `NodeType`, `ActionKind`, `Scope` per design Section 3.1. Include all fields: id, label, type, scope, action_kind, command, children, resolver, timeout_ms, cache_ttl_s, config_file, tags, icon, description, disabled, source_file.
  - **Traces to**: P-04 | R-24

- [ ] **T031: Implement Command Graph YAML loader**
  - **Description**: Create `core/engine/graph/loader.py` — loads node trees from YAML files in `menus/` directories (global, profile, workspace, pack). Each YAML file defines a list of `CommandGraphNode` entries. Validate schema on load. Support auto-discovery of action scripts from `actions/` directories.
  - **Traces to**: P-04 | R-30

- [ ] **T032: Implement scope cascade resolver for nodes**
  - **Description**: Create `core/engine/graph/resolver.py` — merges node trees from global → profile → workspace scope. Nodes merge by ID. Workspace overrides profile overrides global. Groups merge children recursively. `disabled: true` removes inherited nodes. Return fully resolved tree. Unit test with conflicting IDs, disabled nodes, nested groups.
  - **Traces to**: P-04 | R-27

- [ ] **T033: Implement live source resolution**
  - **Description**: Create `core/engine/graph/live_sources.py` — async resolver for Live Source nodes. Each live source has a Python callable (resolver path), timeout, and cache TTL. Resolution runs in asyncio with `asyncio.wait_for(timeout)`. Timed-out sources show placeholder text, never block static nodes. Cache results by TTL. Built-in resolvers: `nexus.live.current_composition`, `nexus.live.current_profile`, `nexus.live.suggested_packs`, `nexus.live.enabled_packs`, `nexus.live.active_tabs`, `nexus.live.processes`, `nexus.live.ports`, `nexus.live.git_status`, `nexus.live.connectors`, `nexus.live.agent_status`.
  - **Traces to**: P-05 | R-28

- [ ] **T034: Build system root menu tree**
  - **Description**: Create the system-generated YAML for the Command Graph landing page (design Section 6): Compositions, Profiles, Packs, Actions (save/restore/reload/scripts), Settings (keymap, theme, HUD, adapters, connectors, workspace, tab bar), Live (tabs, processes, ports, git, connectors, agents), Custom. Ship as `core/ui/menus/system_root.yaml`.
  - **Traces to**: P-04, P-12 | R-24, R-30, R-32

- [ ] **T035: Implement menu_handler.py (nexus-ctl menu open)**
  - **Description**: Create `core/engine/api/menu_handler.py` — handler for Alt+m. Resolves the full Command Graph tree (T032), resolves live sources async (T033), renders through the Menu capability adapter (fzf/gum/Textual). Handles keybindings: Enter (new tab), Shift+Enter (replace tab), Opt+E (edit source), l/Right (expand), h/Left (back), Space (toggle group), / (filter). Returns structured action to caller for tab stack dispatch.
  - **Traces to**: P-04, P-05, P-11, P-12 | R-16, R-24, R-25, R-26, R-28, R-29, R-31, R-32

- [ ] **T036: Implement capability_launcher.py (nexus-ctl capability open)**
  - **Description**: Create `core/engine/api/capability_launcher.py` — handler for Alt+o. Lists all registered capability types from CapabilityRegistry. For each: shows label, current default adapter, available count. Enter opens a new instance of that capability as a tab. Shift+Enter replaces current tab. Alt+e on a capability opens adapter selection (list available tools, Enter sets default, l/Right for one-shot spawn).
  - **Traces to**: P-11 | R-17, R-18, R-19

- [ ] **T037: Migrate existing menu YAMLs to Command Graph format**
  - **Description**: Convert existing menu files in `core/ui/menus/` (home.yaml, settings.yaml, ai.yaml, sovereignty.yaml, keychain.yaml) from the old plane/action format to Command Graph node format. Preserve all existing menu content as nodes in the system tree.
  - **Traces to**: P-04 | R-24

---

## 5. Phase 5: Packs & Profiles

Two-axis model: packs for project needs, profiles for work style.

- [ ] **T040: Implement Pack data model**
  - **Description**: Create `core/engine/packs/pack.py` with `Pack` dataclass per design Section 3.4. Fields: name, version, description, markers, tools, connectors, services, menu_nodes, actions, enabled.
  - **Traces to**: P-07 | R-42, R-43

- [ ] **T041: Implement pack detector**
  - **Description**: Create `core/engine/packs/detector.py` — scans project root for marker files (pyproject.toml, Cargo.toml, Dockerfile, package.json, go.mod, etc.). Cross-references with available packs in `~/.config/nexus/packs/`. Returns list of suggested packs. Never auto-enables — returns suggestions only.
  - **Traces to**: P-07 | R-42

- [ ] **T042: Implement PackManager**
  - **Description**: Create `core/engine/packs/manager.py` — handles enable/disable lifecycle. `enable(pack)`: register tools into CapabilityRegistry, inject menu_nodes into workspace scope, start services, wire connectors to event bus. `disable(pack)`: reverse all of the above. Persist enabled state in `.nexus/workspace.yaml`. Idempotent (P-07).
  - **Traces to**: P-07, P-08 | R-42, R-43, R-44, R-46

- [ ] **T043: Implement nexus-ctl pack commands**
  - **Description**: Wire `nexus-ctl pack {list|suggest|enable|disable}` to PackManager. `suggest`: run detector, show suggestions via Menu capability, prompt user for confirmation before enabling. `enable/disable`: direct toggle. `list`: show all available and their status.
  - **Traces to**: P-07 | R-42, R-43, R-44

- [ ] **T044: Create example packs**
  - **Description**: Write pack YAMLs for 3 domains: Python (markers: pyproject.toml/setup.py, tools: ipython, connectors: test-on-save/jump-to-error, menu: Run Tests/Select Venv/Open REPL), Rust (Cargo.toml, cargo-watch/bacon, build-on-save), Docker (Dockerfile/docker-compose.yaml, lazydocker, container-health live source).
  - **Traces to**: P-07 | R-42, R-43

- [ ] **T045: Profile-pack orthogonality integration test**
  - **Description**: Test that switching profiles does not disable packs, and toggling packs does not change the active profile. Verify both compose independently: same pack + different profile = same tools, different layout. Same profile + different pack = same layout, different tools.
  - **Traces to**: P-08 | R-46

---

## 6. Phase 6: Momentum (Extended)

Extend session persistence with tab stack data and deferred restoration.

- [ ] **T050: Extend MomentumSnapshot with tab stack data**
  - **Description**: Update `core/kernel/layout/save_layout.py` to capture `MomentumSnapshot` per design Section 3.6: session name, dimensions, layout string, active profile, enabled packs, and for each pane: stack_id, role, active_tab_index, and full tab list (capability_type, adapter_name, command, cwd, role, env). Save as JSON to `~/.nexus/state.json`.
  - **Traces to**: P-06 | R-38

- [ ] **T051: Implement deferred restoration**
  - **Description**: Rewrite `core/kernel/layout/restore_layout.sh` (or port to Python) to follow the deferred restoration sequence (design Section 3.6): create session detached → apply layout skeleton → attach (real geometry) → apply proportional coordinates → recreate tab stacks → match by identity → launch commands → activate saved tab index → publish workspace_restored event.
  - **Traces to**: P-06 | R-39, R-40, R-41

- [ ] **T052: Proportional geometry mapping**
  - **Description**: Implement coordinate translation between saved and current screen geometry. Convert absolute pane positions to proportional (w_pct, h_pct, l_pct, t_pct) on save. On restore, map proportionals back to absolute positions at the real terminal size. Handle edge cases: saved 4K → restored laptop, saved portrait → restored landscape.
  - **Traces to**: P-06 | R-40

- [ ] **T053: Momentum save on detach hook**
  - **Description**: Wire tmux `client-detached` hook (existing in nexus.conf) to trigger `nexus-ctl workspace save` automatically. Also support explicit save via `nexus-ctl workspace save` (keymap-triggered). Verify round-trip: detach → close terminal → reopen → attach → everything restored.
  - **Traces to**: P-06 | R-38

---

## 7. Phase 7: Event Bus & Connectors

Extend the existing event bus with typed events and connector wiring.

- [ ] **T060: Extend event bus with typed events**
  - **Description**: Update `core/engine/bus/event_server.py` to use the `EventType` enum (design Section 3.7). Add wildcard subscription support (`test.*` matches `test.started`, `test.passed`). Add typed event validation. Ensure existing pub/sub protocol backward compat.
  - **Traces to**: P-09 | R-50, R-51

- [ ] **T061: Implement dead subscriber detection**
  - **Description**: Add health check in event bus: periodically ping subscribers, remove unreachable ones. On publish failure (broken pipe), immediately remove subscriber. Log removals. Ensure removal doesn't affect other subscribers.
  - **Traces to**: P-09 | R-52

- [ ] **T062: Implement connector engine**
  - **Description**: Create `core/engine/connectors/engine.py` — reads connector definitions from `connectors.yaml` (global + workspace + pack-injected). Each connector: subscribe to trigger event type with optional filter, execute action (shell command or internal nexus-ctl command) on match. Connectors are lightweight event bus subscribers.
  - **Traces to**: P-09 | R-49

- [ ] **T063: Implement nexus-ctl bus commands**
  - **Description**: Wire `nexus-ctl bus {publish|subscribe}`. `publish <type> <json>`: publish event. `subscribe <type>`: stream events to stdout (for scripts/debugging). Used by shell scripts and external tools to participate in the event bus.
  - **Traces to**: P-09 | R-50

- [ ] **T064: Verify circular event history**
  - **Description**: Ensure event bus maintains circular buffer of minimum 1000 events. `history` action returns events filtered by type with limit. Test: publish 1500 events, query history, verify oldest 500 are evicted, newest 1000 are retained.
  - **Traces to**: P-09 | R-53

---

## 8. Phase 8: AI Governance & MCP

Read-only workspace exposure to AI agents.

- [ ] **T070: Implement MCP server**
  - **Description**: Create (or extend existing) MCP server exposing read-only workspace tools per design Section 4.5: `get_workspace_layout`, `get_open_files`, `get_running_processes`, `get_active_packs`, `get_event_history`, `read_config`. Each tool queries live state from StackManager, CapabilityRegistry, PackManager, Event Bus, and scope cascade.
  - **Traces to**: P-14 | R-47, R-57

- [ ] **T071: Implement governance pipeline**
  - **Description**: Create `core/engine/governance/pipeline.py` — enforces separation of powers. AI agents submit proposals (structured intents). Proposals enter pending queue. Human supervisor approves/rejects via `nexus-ctl` or Command Graph menu. Approved proposals execute in isolated environment (subprocess with restricted env). Publish AI events to bus.
  - **Traces to**: P-14 | R-54, R-55

- [ ] **T072: Implement spec lock enforcement**
  - **Description**: When a specification has been approved and locked (e.g., design.md is gated), the system rejects agent attempts to overwrite it. Check file-level locks before allowing writes. Integrate with governance pipeline.
  - **Traces to**: P-14 | R-56

---

## 9. Phase 9: UI Layer & Integration

Compositions, themes, HUD, end-to-end testing.

- [ ] **T080: Unify composition schema**
  - **Description**: The existing 22 compositions use two different JSON schemas (nested tree vs flat pane list). Normalize to a single schema that supports both patterns. Update `WorkspaceOrchestrator` to handle the unified schema. Preserve all existing compositions.
  - **Traces to**: P-01 | R-34

- [ ] **T081: Implement composition hot-switching**
  - **Description**: `nexus-ctl workspace switch-composition <name>` applies a new composition without destroying session state in unaffected panes. Strategy: diff current layout vs target, only create/destroy/move panes that differ. Preserve tab stacks on surviving panes.
  - **Traces to**: P-01 | R-35

- [ ] **T082: Implement theme engine**
  - **Description**: `nexus-ctl config apply-theme <name>` reads theme YAML, applies color tokens to: tmux status line, pane borders, HUD, shell prompt (via env vars). Themes are files in the config cascade. Support live preview (apply immediately, revert on cancel).
  - **Traces to**: P-12 | R-37

- [ ] **T083: Update HUD for tab stack awareness**
  - **Description**: Update the HUD status line to show: active tab label for focused pane, tab count per pane, active profile, enabled pack count. Integrate with StackManager for real-time updates. Configurable modules via `hud.yaml`.
  - **Traces to**: P-02 | R-36

- [ ] **T084: Implement nexus-ctl config reload**
  - **Description**: `nexus-ctl config reload` re-reads all config files through the scope cascade, re-resolves the Command Graph tree, re-applies theme, re-applies keymap overrides, refreshes HUD modules. Publishes `system.config.reloaded` event. No session restart required.
  - **Traces to**: P-04 | R-27

- [ ] **T085: Content renderer routing**
  - **Description**: Implement file-type → renderer routing. When a file is opened/viewed, check MIME type or extension, dispatch to best renderer: markdown → glow/mdcat, mermaid → mermaid-cli, code → bat, images → chafa/timg. Use CapabilityRegistry (RENDERER type) with adapter priority.
  - **Traces to**: P-01 | R-48

---

## 10. Phase 10: End-to-End Verification

Verify all success criteria from requirements.

- [ ] **T090: SC-01 — Install-to-IDE in 60 seconds**
  - **Description**: Time the full install flow: clone → install.sh → nexus start → working IDE layout. Must complete under 60s. Optimize any bottleneck.
  - **Traces to**: SC-01

- [ ] **T091: SC-02 — Alt+m opens Command Graph in <200ms**
  - **Description**: Benchmark Alt+m keystroke to visible menu. Profile and optimize if over 200ms. Target: <150ms.
  - **Traces to**: SC-02

- [ ] **T092: SC-03 — 5-pane workspace save/restore**
  - **Description**: Create workspace with 5+ panes, each with 2+ stacked tabs. Save. Kill session. Restore. Verify all tools resume in correct positions with correct tab stacks.
  - **Traces to**: SC-03

- [ ] **T093: SC-04 through SC-15 — Full success criteria sweep**
  - **Description**: Systematic verification of all remaining success criteria: SC-04 (static + live in menu), SC-05 (pack+profile switching), SC-06 (MCP reads state), SC-07 (all keybindings work), SC-08 (tab rotation <100ms), SC-09 (last-tab warning), SC-10 (pane kill destroys all), SC-11 (scope cascade correctness), SC-12 (live sources async), SC-13 (capability launcher), SC-14 (native tab delegation), SC-15 (tab bar configurable).
  - **Traces to**: SC-04 through SC-15

---

**Verification Rule**: No task may exist without a trace to a Property (Design) or Requirement (Intent). Every task above traces to at least one P-xx, R-xx, or SC-xx.
