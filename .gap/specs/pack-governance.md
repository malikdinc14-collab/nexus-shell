# Spec: Pack Governance

> Defines what packs can and cannot do. Prevents packs from becoming a programming language.

---

## 0. Implementation Status

> **The pack system does not exist in the Rust crates.** The legacy Python implementation (`core/engine/packs/`) has full pack loading, detection, and marker scanning. In Rust, only `EventType::PackEnable` and `EventType::PackDisable` event variants exist in `crates/nexus-engine/src/bus.rs`. All pack structs, validation, lifecycle management, and service control are unimplemented. This spec defines the target Rust architecture.

---

## 1. The Problem

Packs are YAML bundles that declare what a workflow needs. They are powerful because they compose capabilities, connectors, menu nodes, and services into a single definition.

The danger: users and pack authors will want conditionals, branching, dynamic behavior. If we allow it, packs become:
- Ansible playbooks (complex YAML logic that's harder to debug than code)
- A broken DSL (all the complexity of programming, none of the tooling)
- Untestable (no type checker, no linter, no debugger for YAML logic)

This spec prevents that by defining hard limits.

---

## 2. The Rule

> **Packs are composition, not logic. They declare WHAT, never HOW.**

A pack may:
- Declare which capabilities it prefers (`editor: helix`)
- Declare menu nodes with fixed commands (`command: "pytest"`)
- Declare connectors with fixed triggers and actions
- Declare services to start
- Declare HUD modules to enable
- Declare keybinding additions

A pack may NOT:
- Contain conditionals (`if`, `when`, `unless`)
- Contain loops or iteration
- Contain variable interpolation beyond `$NEXUS_HOME` and `$PROJECT_ROOT`
- Contain inline scripts or code blocks
- Reference other packs' state
- Dynamically generate commands at pack-load time

### The Escape Hatch

If someone needs dynamic behavior, they write a **Module** (Level 4 extension), not a pack. Modules are compiled Rust code (or future: WASM plugins) with access to the engine API. The boundary is:

| Need | Solution | Level |
|------|----------|-------|
| "List my virtualenvs dynamically" | Shell content provider in the pack's menu context | 3 (Pack) — but the script is the dynamic part, not the YAML |
| "Run different test commands based on project type" | Module that detects project type and registers the right command | 4 (Module) |
| "Conditionally enable a service" | Module with detection logic | 4 (Module) |
| "Start a test watcher" | Pack `services:` field — the command is fixed, the service manager handles lifecycle | 3 (Pack) |

---

## 3. Pack Schema (Strict)

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique pack identifier (lowercase, hyphens) |
| `version` | semver string | Pack version |
| `description` | string | One-line description |
| `markers` | string[] | File/directory markers for auto-detection |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `capabilities` | map[string, string] | Preferred adapter per capability type |
| `menu_nodes` | MenuNode[] | Command Graph nodes to inject (workspace scope) |
| `connectors` | Connector[] | Event-to-action wiring rules |
| `services` | Service[] | Background processes to manage |
| `hud_modules` | string[] | HUD module identifiers to enable |
| `keybinds` | map[string, string] | Additional keybinding → command mappings |
| `compositions` | Composition[] | Layout definitions (see sub-schema below) |
| `env` | map[string, string] | Environment variables to set |
| `depends` | string[] | Other packs this one requires |

### MenuNode (within pack)

```yaml
menu_nodes:
  - id: pack.python.test        # Must be prefixed with pack.<name>.
    label: "Run Tests"           # Static string only
    type: action                 # Valid MenuNode type
    command: "pytest --tb=short" # Static command string
    icon: "test"                 # Optional
    tags: [python, test]         # Optional, for search
```

**Forbidden in `command`:** backtick execution, `$(...)` subshells, `&&`/`||` conditional logic. Simple pipes are allowed (e.g., `pytest | head -20`) since pipes are data flow, not control flow. The command should be a single logical invocation, not a multi-step script.

**Rationale:** If the command needs logic, it should be a standalone script in the pack's directory, referenced by path: `command: "$PACK_DIR/scripts/smart-test.sh"`. The logic lives in the script, not in the YAML.

> **Acknowledged governance gap:** Pack scripts (`$PACK_DIR/scripts/`) can contain arbitrary logic. The governance rules only cover the YAML surface. Scripts are the user's responsibility — they are analogous to shell aliases or dotfiles. Future: a `pack audit` command could flag scripts that modify state, call network endpoints, or exceed complexity thresholds.

### Connector (within pack)

```yaml
connectors:
  - name: test-on-save              # Descriptive name
    trigger:
      type: fs.file.saved           # Event type (exact or wildcard)
      filter:                       # Optional filters
        pattern: "*.py"
    action:
      shell: "pytest --tb=short -q" # Static command
    scope: workspace                # When this connector is active
```

**Forbidden:** `action.if`, `action.unless`, `action.when`, conditional fields of any kind.

### Service (within pack)

```yaml
services:
  - name: pytest-watcher
    command: "ptw --runner 'pytest --tb=short'"
    restart: on-failure              # on-failure | always | never
    healthcheck:
      command: "pgrep -f ptw"       # Optional health check
      interval_ms: 30000
```

**Forbidden:** `command` with conditionals, dynamic command construction, templating.

### Composition (within pack)

```yaml
compositions:
  - name: dev                     # Unique within this pack
    description: "Development layout with editor + terminal + tests"
    layout:
      direction: horizontal       # horizontal | vertical
      ratio: 0.6                  # Split ratio (0.0-1.0)
      left:                       # First child
        pane_type: editor         # editor | terminal | chat | browser
      right:
        direction: vertical
        ratio: 0.5
        left:
          pane_type: terminal
        right:
          pane_type: terminal
```

A composition is a static layout tree definition. It maps to `LayoutNode` in `crates/nexus-engine/src/layout.rs`. Compositions are pure geometry declarations — no conditional logic, no dynamic pane types. On enable, compositions are registered with the engine and available via `layout.import`.

---

## 4. Variable Expansion (Strictly Limited)

Packs may use exactly these variables in string fields:

| Variable | Expands to | Available in |
|----------|-----------|--------------|
| `$NEXUS_HOME` | Nexus Shell installation directory | All fields |
| `$PROJECT_ROOT` | Current workspace root | All fields |
| `$PACK_DIR` | This pack's directory on disk (not yet implemented — to be set by the pack loader at enable time) | `command`, `payload` fields |

**No other variable expansion is allowed.** No `$USER`, no `$SHELL`, no environment variable passthrough. If a command needs environment context, it reads it at runtime — the pack doesn't inject it.

**Rationale:** Arbitrary variable expansion makes packs environment-dependent and breaks portability. The three allowed variables are stable across surfaces and environments.

**Implementation note:** `$PACK_DIR` does not exist in the current codebase. When the pack loader is built, it must set this variable in the pack's execution environment before running any pack commands.

---

## 5. Validation Rules

### At Pack Load Time

1. **Schema validation:** All required fields present, correct types
2. **ID prefix check:** All `menu_node` IDs must start with `pack.<name>.`
3. **Command safety:** No backticks, no `$(...)`, no `&&`/`||` chains in `command` fields
4. **No forbidden fields:** No `if`, `when`, `unless`, `condition`, `loop`, `for_each` at any nesting level
5. **Marker validity:** At least one marker that can be checked with `Path.exists()` or glob
6. **Dependency resolution:** All packs in `depends` must be available (not necessarily enabled)

### At Pack Enable Time

1. **Marker check:** At least one marker found in the workspace
2. **Capability availability:** Preferred adapters are available (or fallback exists)
3. **Service commands exist:** Commands in `services` resolve to real executables
4. **Conflict detection:** No keybind collisions with currently enabled packs

### Validation Errors

- Schema errors → pack rejected, warning shown, workspace continues without it
- Missing markers → pack not auto-suggested (manual enable still allowed)
- Missing capabilities → pack enabled with warnings, missing features degrade
- Service command not found → service skipped, warning logged

---

## 6. Pack Lifecycle

```
(install)              (detect markers)         (user approves)
ABSENT ──→ AVAILABLE ──────→ SUGGESTED ──────────→ ACTIVE
                ↑                                    │
                │              (user disables)       │
                │           DISABLED ←───────────────┘
                │               │
                │         (re-enable)
                │               ↓
                │            ACTIVE
                │
           (uninstall)
           ABSENT ←── AVAILABLE | DISABLED
```

| State | Meaning |
|-------|---------|
| **ABSENT** | Pack not on disk |
| **AVAILABLE** | Pack installed, schema valid, not active |
| **SUGGESTED** | Markers detected in workspace, pack recommended to user (transient UI state, not persisted) |
| **ACTIVE** | User approved, config applied, services running, connectors wired, menu nodes injected |
| **DISABLED** | User explicitly disabled, everything cleanly removed, pack remains installed |

Activation is atomic — the enable sequence runs start to finish. If any step fails, the pack rolls back to AVAILABLE with a warning. Partial enablement is a bug.

### Install / Uninstall

**Install:** Copy pack directory to `$NEXUS_HOME/packs/<name>/`. Validate schema. Transition: `ABSENT → AVAILABLE`. Emit `pack.install` event.

**Uninstall:** Pack must be DISABLED or AVAILABLE (not ACTIVE). Remove pack directory. Transition: `AVAILABLE|DISABLED → ABSENT`. Emit `pack.uninstall` event. If pack is ACTIVE, the uninstall command must disable it first (running the disable sequence).

### Enable Sequence

1. Validate pack (schema + markers + capabilities)
2. Merge `capabilities` preferences into resolver (pack < profile < workspace override)
3. Inject `menu_nodes` into Command Graph (workspace scope)
4. Wire `connectors` into event bus
5. Start `services` via service manager
6. Apply `keybinds` additions
7. Set `env` variables in session. If another active pack already sets the same variable, last-enabled wins. Engine maintains a reference count per env var for clean removal on disable.
8. Emit `pack.enable` event

### Disable Sequence (reverse order)

1. Stop `services`
2. Remove `connectors` from event bus
3. Remove `menu_nodes` from Command Graph
4. Remove `keybinds`
5. Revert `env` variables — only if no other active pack sets the same variable. Engine maintains a reference count per env var; only unset when count reaches zero.
6. Revert `capabilities` preferences — only if no other active pack overrides the same capability.
7. Emit `pack.disable` event

---

## 7. Pack Isolation

### Packs Cannot

- Access other packs' state or configuration
- Override core keybindings (Alt+h/j/k/l, Alt+m, Alt+n/w, etc.)
- Modify engine internals (bus, state, config cascade)
- Write to files outside their own pack directory
- Execute code at load time (only at enable time, through defined lifecycle)

### Packs Can

- Add menu nodes (scoped to `pack.<name>.*` namespace)
- Add connectors (identified by pack name, removable on disable)
- Add services (managed by service manager, not by the pack itself)
- Add keybindings (only non-conflicting additions, never overrides of core)
- Suggest capability preferences (lower priority than user config)

---

## 8. The Ansible Trap (Why This Matters)

Without governance, this progression is inevitable:

```
Stage 1: command: "pytest"                          ← Fine
Stage 2: command: "if [ -f pytest.ini ]; then..."   ← Creeping
Stage 3: when: "project.type == 'django'"           ← YAML logic
Stage 4: for_each: "$(find . -name '*.py')"         ← Turing-complete YAML
Stage 5: Users debugging YAML like code, no tooling ← Ansible
```

This spec stops at Stage 1. If a pack author reaches Stage 2, the answer is: "Write a script and reference it." If they reach Stage 3, the answer is: "Write a Module."

**The line is: packs compose existing pieces. Modules create new pieces.** Packs are nouns. Modules are verbs.

---

## 9. Migration Path (Legacy Python → Rust)

The legacy Python implementation (`core/engine/packs/`) has pack loading, detection, and marker scanning. The Rust crates have only `EventType::PackEnable`/`PackDisable` event variants. This spec defines the full Rust implementation:

### Rust implementation checklist:

- [ ] Full schema validation at load time
- [ ] Service lifecycle management
- [ ] Connector wiring on enable/disable
- [ ] Menu node injection with namespace enforcement
- [ ] Keybind conflict detection
- [ ] Pack state machine (absent → available → suggested → active ↔ disabled)
- [ ] Pack install/uninstall commands (`nexus-ctl pack install/uninstall <path>`)
- [ ] `pack.yaml` linting tool (`nexus-ctl pack validate <path>`)
