# Nexus Shell Architecture Analysis

**Generated:** 2026-03-16  
**Version Analyzed:** 2.1.0 (Sovereign Pro)

---

# 1. Repository Overview

**Nexus Shell** is a modular terminal IDE framework built on TMUX. It orchestrates CLI/TUI applications into hot-swappable workspace layouts called "compositions". The system provides:

- **Multi-pane terminal management** via TMUX orchestration
- **AI integration** through Sovereign Intelligence Daemon (SID)
- **Event-driven architecture** with Unix socket-based pub/sub event bus
- **State persistence** for session restoration
- **Hot-swappable layouts** defined in JSON compositions
- **Profile-based configuration** system
- **Plugin/extension system** for third-party tool integration

---

# 2. Directory Structure

```
nexus-shell/
├── bin/                    # CLI entry points (nxs, nxs-agent, nxs-chat, etc.)
├── config/                 # User-facing configuration (profiles, themes, keybinds)
│   ├── keybinds/          # Keyboard configuration files
│   ├── profiles/          # Workspace profiles (sovereign, orchestrator, etc.)
│   ├── themes/            # Theme definitions
│   └── nvim/              # Neovim configuration
├── core/                   # Core system logic
│   ├── actions/           # Action handlers (focus, swap, theme)
│   ├── ai/                # AI integration (SID daemon, ask utilities)
│   ├── api/               # Configuration helpers, module registry
│   ├── boot/              # Boot sequence (launcher, guard, doctor)
│   ├── bus/               # Event bus server
│   ├── commands/          # Command handlers (workspace, profile, focus)
│   ├── compositions/      # Layout definitions (JSON)
│   ├── exec/              # Execution utilities (router, keybind handlers)
│   ├── hud/               # HUD rendering system
│   ├── layout/            # Layout engine (processor.py, layout_engine.sh)
│   ├── lib/               # Shared libraries (workspace_manager, navigation)
│   ├── lists/             # Menu list providers
│   ├── menus/             # Menu YAML definitions
│   ├── search/            # Search utilities (grep, find)
│   ├── services/          # Background services
│   ├── stack/             # Stack/tab management system
│   ├── state/             # State engine for persistence
│   ├── themes/            # Theme JSON files
│   └── view/              # View utilities
├── extensions/            # Extension system (plugins)
│   ├── loader.sh          # Extension manager
│   └── grepai/            # grepai extension (semantic search)
├── docs/                   # Documentation
├── examples/              # Example configurations
├── external/              # External dependencies (pi-mono, optillm, openevolve)
├── modules/               # Modular components
│   ├── agents/            # Agent module
│   ├── mcp/               # MCP server
│   ├── menu/              # Menu system
│   ├── render/            # Render module
│   └── web/               # Web module
├── scripts/               # Installation scripts
├── tests/                 # Unit and integration tests
└── data/                  # Runtime data
```

---

# 3. File Inventory

## Core Logic (Shell)

| File | Lines | Purpose |
|------|-------|---------|
| `core/boot/launcher.sh` | 453 | Main station initialization |
| `core/layout/layout_engine.sh` | 240 | Pane layout construction |
| `core/exec/stack_manager.sh` | 262 | Tool stack management |
| `core/exec/router.sh` | 142 | Menu output routing |
| `core/boot/guard.sh` | 133 | Session cleanup |
| `core/api/station_manager.sh` | 126 | Station lifecycle |
| `core/exec/nxs-tab.sh` | 141 | Tab management |
| `core/services/daemon_manager.sh` | 110 | Background service orchestration |

## Core Logic (Python)

| File | Lines | Purpose |
|------|-------|---------|
| `core/layout/processor.py` | 167 | JSON layout processing |
| `core/bus/event_server.py` | 251 | Event bus server |
| `core/ai/sid.py` | 141 | Sovereign Intelligence Daemon |
| `core/state/state_engine.py` | 85 | State persistence |
| `core/api/config_helper.py` | 67 | Configuration loading |

## Interfaces

- `bin/nxs` - Main CLI dispatcher
- `bin/nxs-agent` - Agent interface
- `bin/nxs-chat` - Chat interface
- `bin/nxs-view` - View renderer
- `bin/nxs-hook` - Hook system
- `modules/menu/bin/nexus-menu` - Menu TUI

## Configuration

- `config/profiles/*.yaml` - Workspace profiles
- `config/keybinds/*.conf` - Keybinding configurations
- `config/themes/*.yaml` - Theme definitions
- `core/compositions/*.json` - Layout compositions (23 files)
- `core/config/default_settings.yaml` - Default settings

## Tests

- `tests/unit/test_stack_logic.py` - Stack management tests
- `tests/unit/launcher_logic.bats` - Launcher tests
- `tests/unit/profile_loader.bats` - Profile loading tests
- `tests/unit/workspace_manager.bats` - Workspace tests

---

# 4. Dependency Graph Summary

## Central Files (High Fan-in)

```
launcher.sh ──────► [config_helper.py, station_manager.sh, layout_engine.sh, 
                    boot_loader.sh, event_server.py, sid.py, hud_service.sh]
                    
layout_engine.sh ─► [processor.py, restore_layout.sh, state_engine.sh]

router.sh ────────► [commands/workspace.sh, commands/profile.sh, 
                    commands/focus.sh, exec/dap_handler.sh]
```

## Layer Dependencies

```
bin/nxs (CLI)
    │
    ▼
core/boot/launcher.sh ─────────────────────────────────┐
    │                                                   │
    ├──► core/api/config_helper.py (config loading)     │
    ├──► core/api/station_manager.sh (session mgmt)     │
    ├──► core/layout/layout_engine.sh (pane building)   │
    │        └──► core/layout/processor.py              │
    ├──► core/bus/event_server.py (event bus)           │
    ├──► core/ai/sid.py (AI daemon)                     │
    ├──► core/boot/boot_loader.sh (boot services)       │
    │        └──► modules/menu/lib/core/menu_engine.py  │
    └──► core/services/hud_service.sh (HUD)             │
                                                        │
modules/menu/ ◄─────────────────────────────────────────┘
    └──► menu_engine.py (YAML-driven menu rendering)
            └──► providers/*.py (list providers)
```

## Module Dependencies

```
modules/
├── agents/     → bin/nxs-agent (Universal)
├── menu/       → core/menus/, core/lists/
├── mcp/        → core/api/ (Sovereign)
├── render/     → core/view/
└── web/        → external/pi-mono/
```

---

# 5. Inferred System Components

## Component 1: CLI Interface

**Purpose:** Command dispatch and user interaction entry point  
**Files:** `bin/nxs`, `bin/nxs-agent`, `bin/nxs-chat`  
**Dependencies:** core/boot/*  
**Confidence:** HIGH

## Component 2: Boot System

**Purpose:** Session initialization, guards, cleanup, health checks  
**Files:**
- `core/boot/launcher.sh` - Main orchestrator
- `core/boot/boot_loader.sh` - Service loading
- `core/boot/guard.sh` - Exit handling
- `core/boot/doctor.sh` - Health diagnostics
- `core/boot/theme.sh` - Theme application  
**Dependencies:** core/api/*, core/layout/*  
**Confidence:** HIGH

## Component 3: Layout Engine

**Purpose:** Parse JSON compositions and construct TMUX panes  
**Files:**
- `core/layout/layout_engine.sh` - Shell orchestration
- `core/layout/processor.py` - Recursive pane building
- `core/layout/restore_layout.sh` - Session restoration
- `core/compositions/*.json` - Layout definitions  
**Dependencies:** tmux, core/state/*  
**Confidence:** HIGH

## Component 4: Event Bus (Nervous System)

**Purpose:** Inter-component communication via Unix sockets  
**Files:**
- `core/bus/event_server.py` - Async pub/sub server
- `core/bus/nxs-event` - CLI client  
**Dependencies:** asyncio  
**Confidence:** HIGH

## Component 5: AI Integration Layer

**Purpose:** AI agent coordination and daemon management  
**Files:**
- `core/ai/sid.py` - Sovereign Intelligence Daemon
- `core/ai/nxs-ask.sh` - Query interface
- `core/ai/nxs-ai-stream.sh` - Stream handling  
**Dependencies:** event_server.py, litellm, langchain  
**Confidence:** HIGH

## Component 6: Stack Manager (Indestructible Tabs)

**Purpose:** Tab/pane swapping without process termination  
**Files:**
- `core/stack/nxs-stack` - Main stack manager
- `core/stack/nxs-stack-popup` - Popup interface
- `core/stack/nxs-stack-status.py` - Status display  
**Dependencies:** tmux, core/state/*  
**Confidence:** HIGH

## Component 7: State Engine

**Purpose:** Session persistence and workspace state  
**Files:**
- `core/state/state_engine.py` - State management
- `core/state/state_engine.sh` - Shell wrapper
- `data/state.json` - Persistent storage  
**Dependencies:** json  
**Confidence:** HIGH

## Component 8: Menu System

**Purpose:** YAML-driven cascading menu with fzf integration  
**Files:**
- `modules/menu/lib/core/menu_engine.py` - Core engine
- `modules/menu/lib/providers/*.py` - Data providers
- `core/menus/*.yaml` - Menu definitions  
**Dependencies:** pyyaml, fzf  
**Confidence:** HIGH

## Component 9: HUD System

**Purpose:** Real-time status bar rendering  
**Files:**
- `core/hud/renderer.sh` - Main renderer
- `core/hud/telemetry_aggregator.sh` - Data aggregation
- `core/hud/modules/*` - HUD modules  
**Dependencies:** jq  
**Confidence:** MEDIUM

## Component 10: Router/Dispatcher

**Purpose:** Route menu selections to appropriate handlers  
**Files:**
- `core/exec/router.sh` - Main router
- `core/exec/dispatch.sh` - Command dispatch
- `core/exec/task_runner.sh` - Task execution  
**Dependencies:** core/commands/*  
**Confidence:** HIGH

## Component 11: Extension System (NEW)

**Purpose:** Plugin architecture for third-party tool integration  
**Files:**
- `extensions/loader.sh` - Extension manager
- `extensions/grepai/` - grepai extension (semantic search)
**Dependencies:** core/boot/launcher.sh, bin/nxs  
**Confidence:** HIGH

The extension system provides:
- **Discovery** - Automatic scanning of `extensions/*/manifest.yaml`
- **Installation** - Per-extension install scripts
- **Integration hooks** - search_provider, menu_provider, boot_provider
- **MCP registration** - AI agent tool integration
- **Event bus** - Subscribe/publish events

---

# 6. Runtime Execution Flow

```
1. USER EXECUTES: nxs [project] [--composition X] [--profile Y]
         │
         ▼
2. bin/nxs (dispatcher)
         │ Parses command, routes to launcher.sh
         ▼
3. core/boot/launcher.sh
         │ ├── Identity Guard (prevent recursion)
         │ ├── Path Resolution (NEXUS_HOME, PROJECT_ROOT)
         │ ├── Config Loading (config_helper.py)
         │ ├── Session Check (tmux has-session)
         │ └── Environment Setup
         ▼
4. STATION EXISTS?
         │ NO ──► Create new tmux session
         │         └── Initialize station state
         │ YES ──► Find available window slot
         │          └── Create client session
         ▼
5. START BACKGROUND SERVICES (parallel)
         │ ├── Event Bus (event_server.py) ──► /tmp/nexus_{user}/{project}/bus.sock
         │ ├── SID Daemon (sid.py) ──────────► Subscribes to AI_QUERY events
         │ ├── HUD Service (hud_service.sh)
         │ └── Boot Loader (boot_loader.sh) ──► Executes boot list items
         ▼
6. BUILD LAYOUT (layout_engine.sh)
         │ ├── Load composition JSON
         │ ├── Check for saved session state
         │ ├── Execute processor.py (recursive pane building)
         │ └── Set pane roles (@nexus_role)
         ▼
7. PROPAGATE ENVIRONMENT
         │ └── tmux set-environment (NEXUS_HOME, PROJECT_ROOT, NVIM_PIPE, etc.)
         ▼
8. ATTACH SESSION
         │ └── tmux attach-session -t {CLIENT_SESSION}
         ▼
9. RUNTIME LOOP
         │ ├── User interacts with panes
         │ ├── Menu navigation (nexus-menu)
         │ ├── Stack management (nxs-stack)
         │ ├── Event bus messages
         │ └── AI queries (SID)
         ▼
10. SHUTDOWN (trap cleanup)
         │ ├── Kill background PIDs
         │ ├── Stop boot services
         │ ├── Remove pipes
         │ └── Kill event bus
```

---

# 7. External Integrations

| Integration | Type | Location | Purpose |
|-------------|------|----------|---------|
| **TMUX** | Process | Throughout | Terminal multiplexing, pane management |
| **Neovim** | Editor | `EDITOR_CMD`, `NVIM_PIPE` | Code editing with RPC |
| **Yazi** | File Manager | `NEXUS_FILES` | File explorer |
| **Git** | VCS | `core/boot/conflict_detector.sh` | Branch detection, conflicts |
| **LiteLLM** | Library | `pyproject.toml` | LLM abstraction |
| **Textual** | Library | `pyproject.toml` | TUI framework |
| **OptiLLM** | Service | `external/optillm/` | LLM optimization |
| **OpenEvolve** | Service | `external/openevolve/` | Evolutionary code |
| **pi-mono** | Service | `external/pi-mono/` | PI monorepo tools |
| **Unix Sockets** | IPC | `/tmp/nexus_{user}/{project}/bus.sock` | Event bus |
| **Named Pipes** | IPC | `/tmp/nexus_{user}/pipes/nvim_*.pipe` | Neovim RPC |
| **Named Pipes** | IPC | `/tmp/nexus_{user}/pipes/nvim_*.pipe` | Neovim RPC |

---

# 8. Potential Dead Code

## High Confidence (Unused files with 0 references)

```
core/bus/test_event_bus.sh         - Test script, not called
core/boot/stop.sh                  - May be dead, launcher handles cleanup
core/boot/onboarding.sh            - Not referenced in boot flow
core/boot/nxs-aliases.sh           - Alias definitions, unclear usage
core/boot/load_keybinds.sh         - Keybind loading, may be unused
core/api/unload_brains.sh          - Agent cleanup, no references
core/api/nxs-watch.sh              - Watch utility, no references
core/api/nxs-kill.sh               - Kill utility, no references
core/api/kill_agent.sh             - Agent kill, no references
core/api/classifier.py             - Content classification, unused
core/ai/send_context.sh            - Context sending, no references
core/ai/pipe_error.sh              - Error piping, no references
core/ai/nxs-ask.sh                 - Ask interface, no references
core/ai/nxs-ai-stream.sh           - Stream utility, no references
core/actions/nexus-*.sh            - All action handlers (5 files)
```

## Medium Confidence (Rarely referenced)

```
core/mosaic_generator.py           - Mosaic generation, single use
core/mosaic_engine.sh              - Mosaic engine, single use
core/exec/nxs-openevolve           - External tool wrapper
core/exec/nxs-optillm              - External tool wrapper
core/exec/nxs-probe                - Probe utility
core/exec/nxs-web                  - Web utility
```

---

# 9. Architectural Observations

## Structural Risks

### 1. God File: `launcher.sh` (453 lines)

**Risk:** Excessive responsibilities - session creation, service startup, environment setup, cleanup, layout triggering.  
**Evidence:** Contains 10+ distinct logical phases, multiple trap handlers, inline Python.

### 2. Large External Binaries

### 3. Inconsistent Module Boundaries

**Risk:** `modules/` and `core/` have overlapping responsibilities.  
**Evidence:** Menu logic exists in both `modules/menu/` and `core/menus/`, `core/lists/`.

### 4. Multiple State Systems

**Risk:** State managed in multiple locations with different formats.  
**Evidence:**
- `core/state/state_engine.py` → JSON in `.nexus/state.json`
- `core/stack/nxs-stack` → JSON in `/tmp/nexus_{user}/stacks.json`
- `data/state.json` → Global state

### 5. Configuration Proliferation

**Risk:** 4+ configuration layers with unclear precedence.  
**Evidence:**
- `core/config/default_settings.yaml`
- `~/.config/nexus-shell/settings.yaml`
- `.nexus.yaml` (project)
- Environment variables

## Positive Patterns

### 1. Clean Entry Point

**Strength:** `bin/nxs` provides clear CLI dispatch pattern.

### 2. Event-Driven Architecture

**Strength:** Event bus enables loose coupling between components.

### 3. Composition-Based Layouts

**Strength:** JSON compositions allow declarative workspace definitions.

### 4. Stack Isolation

**Strength:** "Reservoir" pattern keeps background processes alive during swaps.

## Anomalies

### 1. Duplicate workspace_manager.sh

**Evidence:** Exists in both `core/lib/` and `core/workspace/`

### 2. Legacy Code Artifacts

**Evidence:** `docs/archive/jules_analysis/` contains old analysis, `docs/legacy/` has deprecated docs.

### 3. External Directory Size

**Evidence:** `external/` contains 4 full projects (pi-mono, optillm, openevolve, claude-code) that should likely be git submodules.

---

# 10. Machine-Readable Architecture Map

```json
{
  "languages": ["Shell (Bash/Zsh)", "Python", "YAML", "JSON"],
  "entrypoints": [
    {
      "path": "bin/nxs",
      "type": "cli",
      "description": "Main CLI dispatcher"
    },
    {
      "path": "bin/nxs-agent",
      "type": "cli",
      "description": "Agent interface"
    },
    {
      "path": "bin/nxs-chat",
      "type": "cli",
      "description": "Chat interface"
    },
    {
      "path": "core/boot/launcher.sh",
      "type": "script",
      "description": "Main station launcher"
    },
    {
      "path": "core/bus/event_server.py",
      "type": "service",
      "description": "Event bus server"
    },
    {
      "path": "core/ai/sid.py",
      "type": "daemon",
      "description": "Sovereign Intelligence Daemon"
    }
  ],
  "modules": [
    {
      "name": "boot",
      "path": "core/boot/",
      "language": "shell",
      "responsibility": "Session initialization and lifecycle"
    },
    {
      "name": "layout",
      "path": "core/layout/",
      "language": "shell+python",
      "responsibility": "TMUX pane construction from compositions"
    },
    {
      "name": "bus",
      "path": "core/bus/",
      "language": "python",
      "responsibility": "Inter-component event messaging"
    },
    {
      "name": "ai",
      "path": "core/ai/",
      "language": "python+shell",
      "responsibility": "AI integration and daemon management"
    },
    {
      "name": "stack",
      "path": "core/stack/",
      "language": "python",
      "responsibility": "Tab/pane stack management"
    },
    {
      "name": "state",
      "path": "core/state/",
      "language": "python",
      "responsibility": "Session persistence"
    },
    {
      "name": "api",
      "path": "core/api/",
      "language": "python+shell",
      "responsibility": "Configuration and module registry"
    },
    {
      "name": "hud",
      "path": "core/hud/",
      "language": "shell",
      "responsibility": "Status bar rendering"
    },
    {
      "name": "menu",
      "path": "modules/menu/",
      "language": "python",
      "responsibility": "YAML-driven menu system"
    },
    {
      "name": "extensions",
      "path": "extensions/",
      "language": "shell",
      "responsibility": "Plugin/extension management system"
    }
  ],
  "components": [
    {
      "name": "CLI Interface",
      "purpose": "Command dispatch and user entry",
      "files": ["bin/nxs", "bin/nxs-agent", "bin/nxs-chat"],
      "dependencies": ["boot"],
      "confidence": "high"
    },
    {
      "name": "Boot System",
      "purpose": "Session initialization, guards, cleanup",
      "files": ["core/boot/launcher.sh", "core/boot/guard.sh", "core/boot/boot_loader.sh"],
      "dependencies": ["api", "layout"],
      "confidence": "high"
    },
    {
      "name": "Layout Engine",
      "purpose": "Parse compositions, build TMUX panes",
      "files": ["core/layout/layout_engine.sh", "core/layout/processor.py"],
      "dependencies": ["state"],
      "confidence": "high"
    },
    {
      "name": "Event Bus",
      "purpose": "Inter-component pub/sub messaging",
      "files": ["core/bus/event_server.py"],
      "dependencies": [],
      "confidence": "high"
    },
    {
      "name": "AI Integration",
      "purpose": "AI agent coordination",
      "files": ["core/ai/sid.py"],
      "dependencies": ["bus"],
      "confidence": "high"
    },
    {
      "name": "Stack Manager",
      "purpose": "Indestructible tab swapping",
      "files": ["core/stack/nxs-stack"],
      "dependencies": ["state"],
      "confidence": "high"
    },
    {
      "name": "State Engine",
      "purpose": "Session persistence",
      "files": ["core/state/state_engine.py"],
      "dependencies": [],
      "confidence": "high"
    },
    {
      "name": "Menu System",
      "purpose": "Cascading YAML menu rendering",
      "files": ["modules/menu/lib/core/menu_engine.py"],
      "dependencies": [],
      "confidence": "high"
    },
    {
      "name": "HUD System",
      "purpose": "Real-time status rendering",
      "files": ["core/hud/renderer.sh"],
      "dependencies": [],
      "confidence": "medium"
    },
    {
      "name": "Router",
      "purpose": "Route menu selections to handlers",
      "files": ["core/exec/router.sh"],
      "dependencies": ["commands"],
      "confidence": "high"
    },
    {
      "name": "Extension System",
      "purpose": "Plugin architecture for third-party tools",
      "files": ["extensions/loader.sh", "extensions/grepai/"],
      "dependencies": ["boot"],
      "confidence": "high"
    }
  ],
  "files": [
    {"path": "core/boot/launcher.sh", "lines": 453, "type": "shell"},
    {"path": "core/layout/layout_engine.sh", "lines": 240, "type": "shell"},
    {"path": "core/exec/stack_manager.sh", "lines": 262, "type": "shell"},
    {"path": "core/boot/launcher.sh", "lines": 453, "type": "shell"},
    {"path": "core/bus/event_server.py", "lines": 251, "type": "python"},
    {"path": "core/ai/sid.py", "lines": 141, "type": "python"},
    {"path": "core/state/state_engine.py", "lines": 85, "type": "python"},
    {"path": "core/layout/processor.py", "lines": 167, "type": "python"},
    {"path": "modules/menu/lib/core/menu_engine.py", "lines": 287, "type": "python"},
    {"path": "core/stack/nxs-stack", "lines": 287, "type": "python"},
    {"path": "extensions/loader.sh", "lines": 120, "type": "shell"},
    {"path": "extensions/grepai/bin/nxs-grepai", "lines": 95, "type": "shell"},
    {"path": "core/search/nxs-search", "lines": 140, "type": "shell"}
  ],
  "dependencies": [
    {"from": "bin/nxs", "to": "core/boot/launcher.sh"},
    {"from": "core/boot/launcher.sh", "to": "core/api/config_helper.py"},
    {"from": "core/boot/launcher.sh", "to": "core/layout/layout_engine.sh"},
    {"from": "core/boot/launcher.sh", "to": "core/bus/event_server.py"},
    {"from": "core/boot/launcher.sh", "to": "core/ai/sid.py"},
    {"from": "core/layout/layout_engine.sh", "to": "core/layout/processor.py"},
    {"from": "core/layout/layout_engine.sh", "to": "core/state/state_engine.py"},
    {"from": "core/ai/sid.py", "to": "core/bus/event_server.py"},
    {"from": "core/boot/boot_loader.sh", "to": "modules/menu/lib/core/menu_engine.py"},
    {"from": "core/exec/router.sh", "to": "core/commands/workspace.sh"}
  ],
  "external_integrations": [
    {"name": "tmux", "type": "process", "purpose": "terminal multiplexing"},
    {"name": "nvim", "type": "editor", "purpose": "code editing with RPC"},
    {"name": "yazi", "type": "file_manager", "purpose": "file exploration"},
    {"name": "git", "type": "vcs", "purpose": "version control"},
    {"name": "litellm", "type": "library", "purpose": "LLM abstraction"},
    {"name": "langchain", "type": "library", "purpose": "agent framework"},
    {"name": "textual", "type": "library", "purpose": "TUI framework"},
    {"name": "textual", "type": "library", "purpose": "TUI framework"},
    {"name": "unix_sockets", "type": "ipc", "purpose": "event bus communication"},
    {"name": "named_pipes", "type": "ipc", "purpose": "neovim RPC"}
  ],
  "possible_dead_code": [
    "core/bus/test_event_bus.sh",
    "core/boot/stop.sh",
    "core/boot/onboarding.sh",
    "core/boot/nxs-aliases.sh",
    "core/boot/load_keybinds.sh",
    "core/api/unload_brains.sh",
    "core/api/nxs-watch.sh",
    "core/api/nxs-kill.sh",
    "core/api/kill_agent.sh",
    "core/api/classifier.py",
    "core/ai/send_context.sh",
    "core/ai/pipe_error.sh",
    "core/ai/nxs-ask.sh",
    "core/ai/nxs-ai-stream.sh",
    "core/actions/nexus-theme.sh",
    "core/actions/nexus-swap.sh",
    "core/actions/nexus-focus-tree.sh",
    "core/actions/nexus-focus-terminal.sh",
    "core/actions/nexus-focus-editor.sh"
  ]
}
```
