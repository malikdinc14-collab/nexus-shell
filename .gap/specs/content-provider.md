# Spec: Content Provider Contract

> Defines the `ContentProvider` abstraction — the universal interface for feeding data into the menu system.

---

## 0. Implementation Status

> **This spec describes the target architecture.** Content providers, MenuNode, and the layered discovery system do not exist in the Rust crates yet. The legacy Python implementation (`menu_engine.py`) is the reference. The Rust engine currently uses `dispatch.rs` (domain.action routing) instead of the Python command graph. When providers are ported, they will emit `MenuNode` data consumed by a menu domain in the dispatch system — not a reimplementation of the Python command graph.

---

## 1. Core Concept

A **Content Provider** is anything that produces structured data for the menu system. Shell scripts, Rust modules, RPC endpoints, and static YAML files are all implementations of the same abstraction.

### The Invariant

> **The engine consumes data. It never knows or cares how that data was produced.**

A provider's output is a list of `MenuNode` objects (represented as JSON). The engine merges, validates, and renders them through the menu adapter. The provider's internal mechanism — shell, Rust, HTTP, cached file — is invisible to the engine.

### Target Rust Trait

```rust
/// Content provider abstraction — produces MenuNode data for a given context.
///
/// Implementations: YamlProvider, ShellProvider, RpcProvider (future).
/// All providers are sync (shell providers block on subprocess; async wrapper
/// available for daemon context).
pub trait ContentProvider: Send + Sync {
    /// Unique provider identifier (e.g., "yaml:build", "shell:build/list.sh").
    fn id(&self) -> &str;

    /// Produce menu nodes for the given context.
    /// Returns an empty vec on failure (degrade, never block).
    fn provide(&self, context: &str) -> Result<Vec<MenuNode>, ProviderError>;

    /// Portability tier — determines which surfaces can run this provider.
    fn tier(&self) -> PortabilityTier;
}
```

This trait will live in `crates/nexus-engine` when content providers are implemented. The `MenuNode` struct will use `serde` derives for JSON serialization.

---

## 2. MenuNode Schema

Every provider emits JSON objects conforming to this schema. One JSON object per line (NDJSON).

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Display text shown to the user |
| `type` | enum | Node type (see below) |
| `payload` | string | Action target, submenu context, or data |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `icon` | string | `""` | Icon identifier or emoji |
| `description` | string | `""` | Secondary line / tooltip text |
| `tags` | string[] | `[]` | Searchable tags for filtering |
| `verb` | string | `"run"` | How to handle payload: `run`, `edit`, `open`, `push` |
| `id` | string | auto | Unique node identifier |
| `_root` | object | null | Root metadata (only on first item of a provider response) |

### Node Types

| Type | Meaning | Payload contains |
|------|---------|------------------|
| `ACTION` | Execute a command | Shell command string |
| `FOLDER` | Navigate into submenu | Context string for child providers |
| `PLANE` | Navigate into a named context | Context name |
| `LIVE` | Real-time updating node | Resolver identifier |
| `SETTING` | Open config file for editing | File path |
| `SET_DEFAULT` | Set default adapter | `role\|command` |
| `SEPARATOR` | Visual divider | `"NONE"` |
| `STACK_TAB` | Tab in a stack | `role\|index` |
| `INFO` | Non-interactive display | `"NONE"` |
| `ERROR` | Error display | `"NONE"` |
| `DISABLED` | Grayed-out, non-selectable | `"NONE"` |

### Example Output

```jsonl
{"label": "Run Tests", "type": "ACTION", "payload": "pytest --tb=short", "icon": "test", "tags": ["python", "test"]}
{"label": "Deploy Staging", "type": "ACTION", "payload": "./scripts/deploy.sh staging", "icon": "rocket"}
{"label": "Docker Services", "type": "FOLDER", "payload": "build:docker", "icon": "whale"}
{"label": "──────────────", "type": "SEPARATOR", "payload": "NONE"}
{"label": "Settings", "type": "SETTING", "payload": "~/.config/nexus/adapters.yaml", "icon": "gear"}
```

---

## 3. Provider Implementations

### 3.1 Static YAML Provider

**File:** `_list.yaml` in a context directory.

Parsed at menu open time. Contains metadata (name, icon, layout) and optionally static items. No execution, no side effects, fully portable.

```yaml
name: "CI/CD Pipeline"
icon: "hammer"
layout: "list"
items:
  - label: "Run Tests"
    type: ACTION
    payload: "pytest"
    icon: "test"
```

**Portability tier:** Data-portable (works on every surface).

### 3.2 Shell Script Provider

**File:** `list.sh` (or any executable) in a context directory.

Executed as a subprocess. Must emit NDJSON to stdout. Must terminate within timeout.

**Contract:**
- Receives context as first argument: `./list.sh <context>`
- Inherits environment: `$NEXUS_HOME`, `$PROJECT_ROOT`, `$NEXUS_PROFILE`
- Emits zero or more JSON lines to stdout
- Stderr is captured for logging, never shown to user
- Exit code 0 = success. Non-zero = treated as empty output + warning logged.

**Portability tier:** Execution-portable (works on Unix surfaces and server-backed web).

### 3.3 Rust Engine Provider

**Module:** A Rust `impl ContentProvider` compiled into the engine.

Used for providers that need adapter access, complex data processing, or are part of the engine itself. These replace the legacy Python inline providers (`render_home()`, `render_global_tabs()`, `render_modules()` in `menu_engine.py`).

```rust
/// Example: built-in provider that lists active tab stacks.
struct StackTabProvider;

impl ContentProvider for StackTabProvider {
    fn id(&self) -> &str { "engine:stack-tabs" }

    fn provide(&self, _context: &str) -> Result<Vec<MenuNode>, ProviderError> {
        // Access engine state via shared reference
        // Return STACK_TAB nodes for each active tab
        todo!()
    }

    fn tier(&self) -> PortabilityTier { PortabilityTier::Engine }
}
```

**Portability tier:** Engine-portable (runs wherever the Rust engine runs — all surfaces).

### 3.4 RPC / API Provider (Future)

For remote data sources — an HTTP endpoint, a gRPC service, a WebSocket feed.

Not yet needed. When implemented, same MenuNode schema, same validation, same timeout rules.

**Portability tier:** Fully portable (network call, surface-independent).

### 3.5 Cached Provider

A provider whose output is cached with a TTL. Wraps any other provider type.

Useful for expensive queries (e.g., listing remote branches, querying cluster health).

Not yet implemented. When added:
- Cache key: `(provider_id, context)`
- TTL: configurable per provider, default 30s
- Invalidation: event-driven (e.g., `git push` invalidates branch list)

---

## 4. Provider Discovery

The engine discovers providers through a layered filesystem convention:

```
Layer 1 (system):   $NEXUS_HOME/core/engine/lists/<context>/
Layer 2 (builtin):  $NEXUS_HOME/modules/menu/lists/<context>/
Layer 3 (user):     ~/.nexus/lists/<context>/
Layer 4 (profile):  ~/.nexus/profiles/<active_profile>/lists/<context>/
Layer 5 (workspace): $PROJECT_ROOT/.nexus/lists/<context>/
```

Within each layer directory:
- `_list.yaml` → Static YAML provider (metadata + optional items)
- `_shadow` → Exclusion list (names to hide from lower layers)
- `list.sh` or any executable → Shell script provider
- Named scripts (`editor.sh`, `sessions.sh`) → Additional shell providers
- `*.yaml` files (not `_list.yaml`) → Additional static providers

**Legacy Python reference:** `menu_engine.py` `get_list_layers()` at line 66.

**Rust provider discovery.** The filesystem convention above covers YAML and shell providers. Rust engine providers are registered programmatically:
- Engine providers register at init time via `ProviderRegistry::register(Box<dyn ContentProvider>)`
- Pack providers register at pack-enable time (see `pack-governance.md` enable sequence)
- All providers participate in the same merge/shadow/policy rules
- Discovery order: engine providers (system layer) → pack providers (workspace layer) → filesystem providers (all layers)

### Merge Rules

1. Static YAML: last layer wins for metadata; items from all layers concatenated
2. Shell providers: all layers run; results concatenated in layer order
3. Shadow exclusions: any layer can exclude items from lower layers. Matches by `id` field; `id` is **required** for shadowable items. Items without an `id` cannot be shadowed. (Legacy behavior fell back to `label` matching, which was fragile and is deprecated.)
4. Named scripts: same name in higher layer replaces lower layer's script
5. Policy override: `lists.yaml` can set `policy: override` to replace instead of aggregate

---

## 5. Execution Constraints

### Timeout

- Default: **5 seconds** per shell provider
- Configurable per provider via `_list.yaml`: `timeout_ms: 10000`
- On timeout: process killed (SIGTERM, then SIGKILL after 1s), output discarded, warning logged. **Note:** This escalation is the target behavior — neither the legacy Python (`subprocess.timeout`) nor the Rust codebase implements SIGTERM/SIGKILL escalation yet.
- Menu renders with available data — timeout never blocks the UI

### Validation

Every JSON line from a provider is validated:
- Must be valid JSON
- Must have `label` (string) and `type` (valid enum value)
- Missing `payload` defaults to `"NONE"`
- Extra fields are preserved (forward compatibility)
- Invalid lines are skipped with a warning log

### Isolation

- Providers run in a subprocess (shell providers) or function call (Python providers)
- Shell providers cannot modify engine state — they have no channel back except stdout
- Shell providers inherit a controlled environment (see section 3.2)
- Shell providers must not assume any specific surface — no `tmux` commands, no surface-specific calls

### Side Effects

- Providers **should** be side-effect-free (pure data emission)
- Providers **may** perform read-only side effects (query docker, read git state, list files)
- Providers **must not** perform write side effects (modify files, start processes, change state)
- This rule is enforced by convention, not sandbox — violating providers are user's responsibility

---

## 6. Portability Tiers

| Tier | Definition | Examples | Works on |
|------|------------|----------|----------|
| **Data-portable** | Pure data, no execution needed | YAML files, cached JSON | Every surface |
| **Execution-portable** | Requires a Unix-like shell | Shell script providers, action commands | tmux, Sway, Tauri (local), web (server-side) |
| **Engine-portable** | Requires the Rust engine | Rust `impl ContentProvider`, live sources | Wherever engine runs |

### Cross-Surface Behavior

- A YAML menu tree renders identically on every surface
- A shell provider runs on every surface that has server-side access (web included)
- Provider output is the same regardless of surface — rendering differs
- If a surface cannot run a provider type (e.g., browser-only web without server), the provider is skipped with a logged warning

---

## 7. Relationship to Live Sources

Content providers and live sources serve different roles:

| Aspect | Content Provider | Live Source |
|--------|-----------------|-------------|
| When it runs | Once per menu open | Continuously / on timer |
| Output | Static list of MenuNodes | Updating data stream |
| Statefulness | Stateless | May hold subscriptions |
| Who writes them | Users, packs | Engine, packs (Rust engine) |
| Side effects | Read-only at most | Queries adapter state |

A content provider answers: "What items should appear in this menu?"
A live source answers: "What is the current state of this system metric?"

Both produce data consumed by the Command Graph. They are complementary, not competitive.

---

## 8. Migration Path (Legacy Python → Rust)

The legacy Python `menu_engine.py` implements most of this spec informally:
- Layered discovery via `get_list_layers()` ✓
- YAML + shell providers ✓
- NDJSON output format ✓
- Shadow exclusions ✓
- Merge policies ✓

### Rust implementation checklist:
- [ ] Define `MenuNode` struct with serde derives in `crates/nexus-engine`
- [ ] Define `ContentProvider` trait (see section 1)
- [ ] Define `ProviderError` and `PortabilityTier` types
- [ ] Implement `YamlProvider` (parse `_list.yaml`)
- [ ] Implement `ShellProvider` (subprocess with timeout via `tokio::process`)
- [ ] Implement `ProviderRegistry` with layered merge/shadow logic
- [ ] Add `menu.open` and `menu.navigate` actions to `dispatch.rs`
- [ ] Formal SIGTERM/SIGKILL timeout enforcement
- [ ] MenuNode JSON schema validation at provider output boundary
- [ ] Cached provider wrapper (TTL + event-driven invalidation)
- [ ] Shadow matching by `id` only (deprecate `label` fallback)

### What the Rust codebase has today:
- `CapabilityRegistry` in `registry.rs` — adapter selection (not provider discovery, but analogous pattern)
- `dispatch.rs` — 11 domains, ~30 actions. Menu providers will add a `menu` domain.
- `EventBus` — can drive event-based cache invalidation for `CachedProvider`
