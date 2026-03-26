# Structural Design: nexus-shell

## 1. Architecture Overview

Three-layer architecture: **Tools** (adapters) → **Connectors** (event bus + wiring) → **Services** (engine, orchestration, persistence).

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│  Modeless Keymap (Alt+*)  │  Command Graph  │  Tab Bar/HUD  │
├─────────────────────────────────────────────────────────────┤
│                    ORCHESTRATION LAYER                        │
│  Intent Resolver → Planner → Executor                        │
│  Capability Registry ←→ Adapter Pool                         │
│  Scope Cascade Engine (workspace > profile > global)         │
├─────────────────────────────────────────────────────────────┤
│                     SERVICES LAYER                            │
│  Tab Stack   │ Momentum  │ Pack/Profile │ Command Graph      │
│  Manager     │ Engine    │ Manager      │ Resolver           │
├─────────────────────────────────────────────────────────────┤
│                    CONNECTORS LAYER                           │
│  Event Bus (Unix socket pub/sub)                             │
│  Connectors: editor↔test, file↔render, ai↔workspace         │
├─────────────────────────────────────────────────────────────┤
│                      TOOLS LAYER                             │
│  Adapters: Neovim│Yazi│tmux│fzf│gum│OpenCode│lazygit│btop   │
│  Null Adapters: NullMultiplexer│NullMenu                     │
└─────────────────────────────────────────────────────────────┘
```

**Component Relationships:**

```
User Input (Alt+key)
  │
  ▼
tmux keybind → shell handler (bash/python)
  │
  ▼
Intent Resolver ──→ CapabilityRegistry.get_best(type)
  │                        │
  ▼                        ▼
Planner ──→ Executor ──→ Adapter.execute()
  │                        │
  ▼                        ▼
Tab Stack Manager     Event Bus (publish result)
  │                        │
  ▼                        ▼
Momentum (persist)    Connectors (react)
```

---

## 2. Correctness Properties

Verifiable invariants that must always hold. Each property validates one or more requirements.

*   **P-01**: Every intent dispatched through the engine resolves to exactly one adapter or produces an explicit fallback error — never silently drops. — *Validates: R-01, R-02, R-03*
*   **P-02**: A pane's tab stack is the single source of truth for what is running in that pane. No tool can exist in a pane without a corresponding stack entry (or native delegation). — *Validates: R-05, R-06, R-12*
*   **P-03**: Tab stack operations (push, pop, rotate) are atomic — no intermediate state is visible to the user. A rotate never shows an empty pane. — *Validates: R-07, R-08*
*   **P-04**: The Command Graph node tree is a pure function of (global_nodes ∪ profile_nodes ∪ workspace_nodes) with workspace taking precedence by node ID. The same inputs always produce the same tree. — *Validates: R-24, R-27*
*   **P-05**: Live Source resolution never blocks static node rendering. A timed-out Live Source shows a placeholder, never hangs the menu. — *Validates: R-28*
*   **P-06**: Momentum save captures sufficient state to restore the workspace on a different screen geometry. Restoration uses proportional coordinates, never absolute pixel positions. — *Validates: R-38, R-39, R-40, R-41*
*   **P-07**: Pack enable/disable is idempotent — enabling an already-enabled pack is a no-op; disabling removes exactly its registered resources with no side effects on other packs. — *Validates: R-42, R-43, R-44*
*   **P-08**: Profiles and packs are orthogonal — changing a profile never disables packs, and vice versa. Their intersection is the workspace scope. — *Validates: R-46*
*   **P-09**: Event bus message delivery is at-most-once with dead subscriber detection. No message queues indefinitely for a dead subscriber. — *Validates: R-51, R-52*
*   **P-10**: All keybindings are Alt+key with no prefix. No keybinding requires entering a mode. — *Validates: R-14*
*   **P-11**: Enter always opens as new tab; Shift+Enter always replaces current tab. This holds in every context: Command Graph, capability launcher, tab manager. — *Validates: R-23, R-25, R-18*
*   **P-12**: Settings are files. No setting requires inline menu editing. Opt+E on any Setting node opens the backing file in the editor. — *Validates: R-32*
*   **P-13**: The Menu capability has a null adapter. If no renderer (fzf/gum/Textual) is available, the system degrades gracefully rather than crashing. — *Validates: R-33*
*   **P-14**: AI agents can read but never directly write workspace state. All mutations go through the governance approval pipeline. — *Validates: R-54, R-57*

---

## 3. Data Models

### 3.1 Command Graph Node

The fundamental unit of the Command Graph. All menu content is a node.

```python
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from uuid import UUID, uuid4

class NodeType(Enum):
    ACTION = "action"
    GROUP = "group"
    LIVE_SOURCE = "live_source"
    SETTING = "setting"

class ActionKind(Enum):
    SHELL = "shell"          # Execute shell command
    PYTHON = "python"        # Execute Python callable
    INTERNAL = "internal"    # Nexus internal operation
    NAVIGATION = "navigation"  # Navigate to another menu plane

class Scope(Enum):
    GLOBAL = "global"
    PROFILE = "profile"
    WORKSPACE = "workspace"

@dataclass
class CommandGraphNode:
    """A single node in the Command Graph tree."""
    id: str                              # Unique within scope (e.g., "settings.keymap")
    label: str                           # Display label
    type: NodeType                       # action | group | live_source | setting
    scope: Scope = Scope.GLOBAL          # Resolution scope

    # Action fields
    action_kind: Optional[ActionKind] = None
    command: Optional[str] = None        # Shell command, Python path, or internal ID

    # Group fields
    children: List['CommandGraphNode'] = field(default_factory=list)

    # Live Source fields
    resolver: Optional[str] = None       # Python callable path for async resolution
    timeout_ms: int = 3000               # Max resolution time
    cache_ttl_s: int = 30                # Cache duration

    # Setting fields
    config_file: Optional[str] = None    # Path to backing config file

    # Common fields
    tags: List[str] = field(default_factory=list)  # For search/filter
    icon: Optional[str] = None
    description: Optional[str] = None
    disabled: bool = False               # Can be disabled by higher scope
    source_file: Optional[str] = None    # Where this node was defined (for Opt+E)
```

**Node Resolution Algorithm:**

```
resolve_tree(scope_chain: [global, profile, workspace]) → tree:
    merged = {}
    for scope in scope_chain:
        for node in scope.nodes:
            if node.id in merged:
                if node.disabled:
                    del merged[node.id]
                else:
                    merged[node.id] = merge_node(merged[node.id], node)
            else:
                merged[node.id] = node
    return build_tree(merged)

merge_node(base, override) → node:
    # Override wins for all scalar fields
    # Children: merge recursively by child.id
    # Tags: union
```

### 3.2 Tab Stack

The data model for a pane's layered tool stack.

```python
@dataclass
class Tab:
    """A single tab within a pane stack."""
    id: str                        # UUID
    capability_type: str           # "editor", "terminal", "chat", "menu", etc.
    adapter_name: str              # "neovim", "zsh", "opencode", "fzf", etc.
    tmux_pane_id: Optional[str]    # Physical tmux pane (None if in reservoir)
    command: str                   # Launch command
    cwd: str                       # Working directory
    role: Optional[str]            # User-assigned role tag
    env: Dict[str, str] = field(default_factory=dict)
    is_active: bool = False        # Currently visible in the stack
    native_multiplicity: bool = False  # Adapter handles its own tabs

@dataclass
class TabStack:
    """The stack of tabs in a single pane."""
    id: str                        # UUID — survives across sessions
    pane_id: str                   # tmux pane identifier
    tabs: List[Tab] = field(default_factory=list)
    active_index: int = 0          # Index of currently visible tab
    role: Optional[str] = None     # User-assigned stack identity

    @property
    def active_tab(self) -> Optional[Tab]:
        if self.tabs:
            return self.tabs[self.active_index]
        return None

    def push(self, tab: Tab) -> None:
        """Push a new tab, making it active."""
        tab.is_active = True
        if self.tabs:
            self.tabs[self.active_index].is_active = False
        self.tabs.append(tab)
        self.active_index = len(self.tabs) - 1

    def pop(self) -> Optional[Tab]:
        """Remove the active tab and activate the next."""
        if not self.tabs:
            return None
        removed = self.tabs.pop(self.active_index)
        removed.is_active = False
        if self.tabs:
            self.active_index = min(self.active_index, len(self.tabs) - 1)
            self.tabs[self.active_index].is_active = True
        return removed

    def rotate(self, direction: int) -> None:
        """Rotate through tabs. direction: +1 (right/]) or -1 (left/[)."""
        if len(self.tabs) <= 1:
            return
        self.tabs[self.active_index].is_active = False
        self.active_index = (self.active_index + direction) % len(self.tabs)
        self.tabs[self.active_index].is_active = True
```

**Logical Reservoir:**

```python
@dataclass
class TabReservoir:
    """Background tabs not assigned to any visible pane."""
    tabs: List[Tab] = field(default_factory=list)

    def shelve(self, tab: Tab) -> None:
        """Move a tab to the reservoir (keep alive, remove from pane)."""
        tab.is_active = False
        tab.tmux_pane_id = None
        self.tabs.append(tab)

    def recall(self, tab_id: str, target_pane_id: str) -> Optional[Tab]:
        """Pull a tab from reservoir into a pane."""
        for i, tab in enumerate(self.tabs):
            if tab.id == tab_id:
                tab.tmux_pane_id = target_pane_id
                return self.tabs.pop(i)
        return None
```

### 3.3 Capability Adapter Contract

Extends the existing `CapabilityType` enum and adapter base class.

```python
@dataclass
class AdapterManifest:
    """Metadata every adapter must declare."""
    name: str                        # "neovim", "yazi", "fzf", etc.
    capability_type: CapabilityType  # EDITOR, EXPLORER, MENU, etc.
    priority: int = 100              # Higher = preferred
    native_multiplicity: bool = False  # Can this tool manage its own tabs?
    binary: str = ""                 # Binary name for availability check
    binary_candidates: List[str] = field(default_factory=list)
    install_hint: Optional[str] = None
    mcp_enabled: bool = False        # Supports MCP protocol

    def is_available(self) -> bool:
        """Check if the adapter's binary exists on PATH."""
        candidates = [self.binary] + self.binary_candidates
        return any(shutil.which(b) for b in candidates)
```

**Null Adapter Pattern:**

```python
class NullMenuAdapter(MenuCapability):
    """Graceful degradation when no menu renderer is available."""
    manifest = AdapterManifest(
        name="null-menu",
        capability_type=CapabilityType.MENU,
        priority=0,
        native_multiplicity=False,
        binary="true",  # Always available
    )

    def show_menu(self, options, prompt="") -> Optional[str]:
        # Fall back to simple numbered selection via stdin
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
        try:
            choice = input(f"{prompt}> ")
            return options[int(choice) - 1]
        except (ValueError, IndexError):
            return None

    def pick(self, context, items_json) -> Optional[str]:
        return self.show_menu(items_json, context)
```

### 3.4 Pack

```python
@dataclass
class Pack:
    """A domain capability bundle."""
    name: str                           # "python", "rust", "kubernetes"
    version: str
    description: str

    # Detection
    markers: List[str]                  # File markers: ["pyproject.toml", "setup.py"]

    # What the pack provides
    tools: Dict[str, str]               # capability_type → preferred adapter
    connectors: List[Dict[str, Any]]    # Event bus wiring rules
    services: List[Dict[str, Any]]      # Background services to start
    menu_nodes: List[Dict[str, Any]]    # Command Graph nodes to inject (workspace scope)
    actions: List[Dict[str, Any]]       # Scripts in .nexus/actions/

    # State
    enabled: bool = False
```

**Pack YAML schema:**

```yaml
# .nexus/packs/python.yaml or ~/.config/nexus/packs/python.yaml
name: python
version: "1.0.0"
description: "Python development pack"

markers:
  - pyproject.toml
  - setup.py
  - requirements.txt

tools:
  executor: ipython

connectors:
  - name: test-on-save
    trigger: { type: FS_EVENT, data: { action: file_saved, pattern: "*.py" } }
    action: { shell: "pytest --tb=short -q" }
  - name: jump-to-error
    trigger: { type: TEST_EVENT, data: { status: failed } }
    action: { internal: "editor.goto", args: { file: "$file", line: "$line" } }

services:
  - name: pytest-watcher
    command: "ptw --runner 'pytest --tb=short'"
    restart: on-failure

menu_nodes:
  - id: pack.python.run-tests
    label: "Run Tests"
    type: action
    command: "pytest"
    tags: [python, test]
  - id: pack.python.select-venv
    label: "Select Virtualenv"
    type: action
    command: "nexus-ctl pack python select-venv"
    tags: [python, venv]
  - id: pack.python.repl
    label: "Open REPL"
    type: action
    command: "ipython"
    tags: [python, repl]
```

### 3.5 Profile

Extends the existing profile schema to align with the two-axis model.

```yaml
# ~/.config/nexus/profiles/devops.yaml
name: devops
description: "Monitoring-heavy layout for infrastructure work"

composition: devops            # Default composition to apply
theme: solarized-dark
hud:
  modules: [tabs, mesh, dock, clock]
  refresh_ms: 2000

keybind_overrides:
  # Profile-level keybind additions (cannot remove core Alt+* bindings)
  Alt+k: "kubectl get pods"    # Override Alt+k in devops context

menu_nodes:
  - id: profile.devops.cluster-health
    label: "Cluster Health"
    type: live_source
    resolver: "nexus.live.k8s_health"
    timeout_ms: 5000
    tags: [devops, k8s]

env:
  KUBECONFIG: "~/.kube/config"
```

### 3.6 Momentum Snapshot

Extends the existing Moment model with tab stack data.

```python
@dataclass
class MomentumSnapshot:
    """Complete workspace state for persistence."""
    session_name: str
    timestamp: str                     # ISO 8601
    dimensions: Dict[str, int]         # {"w": 220, "h": 50}
    layout_string: str                 # tmux layout string (for deferred restore)
    active_profile: Optional[str]
    enabled_packs: List[str]

    windows: List['WindowSnapshot']

@dataclass
class WindowSnapshot:
    """State of a single tmux window."""
    index: int
    name: str
    project_root: str
    panes: List['PaneSnapshot']

@dataclass
class PaneSnapshot:
    """State of a single pane including its tab stack."""
    stack_id: str                      # TabStack UUID (for identity-based reconnection)
    role: Optional[str]
    active_tab_index: int
    tabs: List['TabSnapshot']
    geom: Dict[str, float]            # Proportional: {"w_pct", "h_pct", "l_pct", "t_pct"}

@dataclass
class TabSnapshot:
    """State of a single tab for restoration."""
    capability_type: str
    adapter_name: str
    command: str
    cwd: str
    role: Optional[str]
    env: Dict[str, str]
```

**Deferred Restoration Sequence:**

```
1. tmux new-session (detached, hidden)
2. Create panes from layout_string (skeleton)
3. tmux attach (terminal reports real geometry)
4. apply_proportional_geometry(snapshot.dimensions → real dimensions)
5. For each pane:
   a. Create TabStack with saved stack_id
   b. Match by identity (stack_id, role), not pane index
   c. For each tab: push onto stack, launch command in cwd
   d. Activate the saved active_tab_index
6. Publish UI_EVENT: workspace_restored
```

### 3.7 Event Types

```python
class EventType(Enum):
    # Filesystem
    FS_FILE_OPENED = "fs.file.opened"
    FS_FILE_SAVED = "fs.file.saved"
    FS_FILE_CLOSED = "fs.file.closed"

    # Editor
    EDITOR_BUFFER_CHANGED = "editor.buffer.changed"
    EDITOR_CURSOR_MOVED = "editor.cursor.moved"

    # Test
    TEST_STARTED = "test.started"
    TEST_PASSED = "test.passed"
    TEST_FAILED = "test.failed"

    # UI / Navigation
    UI_PANE_FOCUSED = "ui.pane.focused"
    UI_TAB_PUSHED = "ui.tab.pushed"
    UI_TAB_POPPED = "ui.tab.popped"
    UI_TAB_ROTATED = "ui.tab.rotated"
    UI_COMPOSITION_SWITCHED = "ui.composition.switched"
    UI_WORKSPACE_RESTORED = "ui.workspace.restored"

    # Pack / Profile
    PACK_ENABLED = "pack.enabled"
    PACK_DISABLED = "pack.disabled"
    PROFILE_SWITCHED = "profile.switched"

    # AI
    AI_PROPOSAL_SUBMITTED = "ai.proposal.submitted"
    AI_PROPOSAL_APPROVED = "ai.proposal.approved"
    AI_PROPOSAL_REJECTED = "ai.proposal.rejected"

    # System
    SYSTEM_CONFIG_RELOADED = "system.config.reloaded"
```

---

## 4. Interface Contracts

### 4.1 Keybinding → Handler Map

Every Alt+key binding routes through tmux to a handler script/command.

| Keybind | tmux binding | Handler | Requirement |
|---------|-------------|---------|-------------|
| Alt+h/j/k/l | `bind -n M-{h,j,k,l} select-pane -{L,D,U,R}` | tmux native | R-15 |
| Alt+m | `bind -n M-m run-shell "nexus-ctl menu open"` | `core/engine/api/menu_handler.py` | R-16 |
| Alt+o | `bind -n M-o run-shell "nexus-ctl capability open"` | `core/engine/api/capability_launcher.py` | R-17 |
| Alt+e | Handled within capability launcher (menu keypress) | Menu adapter internal | R-19 |
| Alt+t | `bind -n M-t run-shell "nexus-ctl tabs list"` | `core/engine/api/tab_manager.py` | R-20 |
| Alt+n | `bind -n M-n run-shell "nexus-ctl stack push"` | `core/engine/api/stack_handler.py` | R-06 |
| Alt+w | `bind -n M-w run-shell "nexus-ctl stack pop"` | `core/engine/api/stack_handler.py` | R-08 |
| Alt+q | `bind -n M-q run-shell "nexus-ctl pane kill"` | `core/engine/api/pane_handler.py` | R-21 |
| Alt+[ | `bind -n M-[ run-shell "nexus-ctl stack rotate -1"` | `core/engine/api/stack_handler.py` | R-07 |
| Alt+] | `bind -n M-] run-shell "nexus-ctl stack rotate +1"` | `core/engine/api/stack_handler.py` | R-07 |
| Alt+v | `bind -n M-v run-shell "nexus-ctl pane split-v"` | `core/engine/api/pane_handler.py` | R-22 |
| Alt+s | `bind -n M-s run-shell "nexus-ctl pane split-h"` | `core/engine/api/pane_handler.py` | R-22 |

### 4.2 nexus-ctl CLI

The unified control interface. All keybindings route through this.

```
nexus-ctl <domain> <action> [args]

Domains:
  menu        Command Graph operations
  capability  Capability launcher
  stack       Tab stack operations
  tabs        Tab manager
  pane        Pane operations
  workspace   Workspace/session operations
  pack        Pack management
  profile     Profile management
  config      Configuration management
  bus         Event bus operations

Examples:
  nexus-ctl menu open                   # Open Command Graph landing page
  nexus-ctl capability open             # Open capability launcher
  nexus-ctl stack push                  # Push new tab onto focused stack
  nexus-ctl stack pop                   # Pop active tab (with last-tab warning)
  nexus-ctl stack rotate +1             # Rotate right through tabs
  nexus-ctl stack rotate -1             # Rotate left through tabs
  nexus-ctl tabs list                   # List active tabs in focused stack
  nexus-ctl pane kill                   # Kill focused pane and all tabs
  nexus-ctl pane split-v                # Split vertical, new anonymous stack
  nexus-ctl pane split-h                # Split horizontal, new anonymous stack
  nexus-ctl workspace save              # Explicit momentum save
  nexus-ctl workspace restore [name]    # Restore from snapshot
  nexus-ctl pack list                   # List available packs
  nexus-ctl pack enable <name>          # Enable pack (with confirmation)
  nexus-ctl pack disable <name>         # Disable pack
  nexus-ctl pack suggest                # Detect project markers, suggest packs
  nexus-ctl profile switch <name>       # Switch active profile
  nexus-ctl profile list                # List available profiles
  nexus-ctl config reload               # Reload all config files
  nexus-ctl bus publish <type> <json>   # Publish event to bus
  nexus-ctl bus subscribe <type>        # Subscribe to event type (stream)
```

### 4.3 Command Graph Menu Interaction

Within the menu (rendered by fzf/gum/Textual adapter):

| Key | Action | Implementation |
|-----|--------|---------------|
| Enter | Execute node → result opens as new tab | Menu adapter returns `{action: "exec", mode: "new_tab", node_id}` |
| Shift+Enter | Execute node → result replaces current tab | Menu adapter returns `{action: "exec", mode: "replace", node_id}` |
| Opt+E | Open node source in editor tab | Menu adapter returns `{action: "edit", node_id}` → `nexus-ctl stack push editor <source_file>` |
| l / Right | Expand submenu or adapter list | Menu adapter navigates into group children |
| h / Left | Go back to parent group | Menu adapter navigates up |
| j/k / Up/Down | Navigate items | Menu adapter native |
| Space | Expand/collapse group | Menu adapter toggle |
| / | Filter/search | Menu adapter search mode |
| Esc / q | Close menu | Menu adapter exits |

### 4.4 Event Bus Protocol

Over Unix domain socket at `/tmp/nexus_$USER/$PROJECT/bus.sock`.

```json
// Subscribe
→ {"action": "subscribe", "types": ["fs.file.saved", "test.*"]}
← {"action": "subscribed", "types": ["fs.file.saved", "test.*"]}

// Publish
→ {"action": "publish", "event": {"type": "fs.file.saved", "source": "nvim", "data": {"path": "/foo.py"}}}
← {"action": "published", "id": "evt-uuid"}

// History query
→ {"action": "history", "type": "test.*", "limit": 50}
← {"action": "history", "events": [...]}

// Unsubscribe
→ {"action": "unsubscribe", "types": ["fs.file.saved"]}
```

Wildcard matching: `test.*` matches `test.started`, `test.passed`, `test.failed`.

### 4.5 MCP Server Interface

Exposes workspace state to AI agents (read-only).

```json
// Tools exposed via MCP
{
  "tools": [
    {
      "name": "get_workspace_layout",
      "description": "Get current pane layout with tab stacks, roles, and running commands"
    },
    {
      "name": "get_open_files",
      "description": "List files open in editor tabs across all panes"
    },
    {
      "name": "get_running_processes",
      "description": "List active processes in all panes"
    },
    {
      "name": "get_active_packs",
      "description": "List enabled packs and their registered resources"
    },
    {
      "name": "get_event_history",
      "description": "Query recent events from the event bus"
    },
    {
      "name": "read_config",
      "description": "Read current configuration (resolved scope cascade)"
    }
  ]
}
```

---

## 5. Configuration Architecture

### 5.1 File Cascade

Three-tier resolution: workspace `.nexus/` overrides profile overrides global `~/.config/nexus/`.

```
~/.config/nexus/                    # GLOBAL scope
├── keymap.conf                     # Global keybind overrides
├── theme.yaml                      # Default theme
├── hud.yaml                        # Default HUD config
├── adapters.yaml                   # Default tool for each capability
├── connectors.yaml                 # Global connector wiring
├── profiles/                       # Available profiles
│   ├── devops.yaml
│   ├── minimalist.yaml
│   └── music.yaml
├── packs/                          # Available packs
│   ├── python.yaml
│   ├── rust.yaml
│   └── kubernetes.yaml
├── compositions/                   # User-defined compositions
├── actions/                        # Global scripts
│   ├── backup.sh
│   └── sync-dots.sh
└── menus/                          # Custom menu YAML trees

.nexus/                             # WORKSPACE scope (per project)
├── workspace.yaml                  # Active profile, enabled packs, overrides
├── keymap.conf                     # Workspace keybind overrides
├── theme.yaml                      # Workspace theme override
├── adapters.yaml                   # Workspace adapter overrides
├── connectors.yaml                 # Workspace connectors
├── compositions/                   # Project-specific compositions
├── actions/                        # Project scripts (auto-discovered)
│   ├── run-tests.sh
│   └── deploy.sh
└── menus/                          # Project-specific menu trees
```

### 5.2 Key Config Schemas

**workspace.yaml** — the workspace root config:
```yaml
# .nexus/workspace.yaml
profile: devops                     # Active profile name
packs:
  - python                          # Enabled packs
  - docker
theme: catppuccin                   # Workspace theme override (wins over profile)
adapters:
  editor: helix                     # Override default editor for this project
```

**keymap.conf** — keybinding overrides:
```conf
# Lines format: <key> = <nexus-ctl command>
# Only overrides — core Alt+* bindings are defined in nexus.conf
# Profile keybinds merge between global and workspace
Alt+F5 = nexus-ctl workspace save
Alt+F9 = nexus-ctl workspace restore
Alt+p  = nexus-ctl pack suggest
```

**adapters.yaml** — default tool per capability:
```yaml
# ~/.config/nexus/adapters.yaml
editor: neovim
explorer: yazi
chat: opencode
menu: fzf
multiplexer: tmux
agent: opencode
executor: zsh
renderer: bat
```

**hud.yaml** — HUD telemetry modules:
```yaml
# ~/.config/nexus/hud.yaml
modules:
  - name: tabs
    position: left
    refresh_ms: 1000
  - name: git
    position: center
    refresh_ms: 5000
  - name: clock
    position: right
    refresh_ms: 60000
separator: " │ "
```

**connectors.yaml** — event bus wiring:
```yaml
# ~/.config/nexus/connectors.yaml
connectors:
  - name: test-on-save
    trigger:
      type: fs.file.saved
      filter: { pattern: "*.py" }
    action:
      shell: "pytest --tb=short -q"
    scope: workspace                   # Only active if workspace has python pack

  - name: format-on-save
    trigger:
      type: fs.file.saved
    action:
      shell: "nexus-ctl capability exec formatter $file"
    scope: global
```

### 5.3 Scope Resolution

```python
def resolve_config(key: str) -> Any:
    """Resolve a config value through the cascade."""
    workspace_val = read_config(".nexus/", key)
    if workspace_val is not None:
        return workspace_val

    profile_name = resolve_config("profile")  # recursive for profile
    if profile_name:
        profile_val = read_config(f"~/.config/nexus/profiles/{profile_name}.yaml", key)
        if profile_val is not None:
            return profile_val

    global_val = read_config("~/.config/nexus/", key)
    return global_val
```

---

## 6. Command Graph Menu Structure

The full node tree for the Command Graph landing page (Alt+m).

```yaml
# System-generated root tree — merges with user/pack/profile nodes
root:
  - id: compositions
    label: "Compositions"
    type: group
    icon: "layout"
    children:
      # Auto-populated from compositions/ directories
      # Enter = switch to composition (nexus-ctl workspace switch-composition <name>)
      # Opt+E = open composition JSON in editor
      - id: compositions.current
        label: "(active: {current_composition})"
        type: live_source
        resolver: "nexus.live.current_composition"

  - id: profiles
    label: "Profiles"
    type: group
    icon: "user"
    children:
      # Auto-populated from profiles/ directory
      # Enter = activate profile (nexus-ctl profile switch <name>)
      # Opt+E = open profile YAML in editor
      - id: profiles.current
        label: "(active: {current_profile})"
        type: live_source
        resolver: "nexus.live.current_profile"

  - id: packs
    label: "Packs"
    type: group
    icon: "package"
    children:
      # Auto-populated from packs/ directory + detected markers
      # Enter = toggle enable/disable (nexus-ctl pack toggle <name>)
      # Opt+E = open pack YAML in editor
      - id: packs.suggested
        label: "Suggested for this project"
        type: live_source
        resolver: "nexus.live.suggested_packs"
      - id: packs.enabled
        label: "Currently enabled"
        type: live_source
        resolver: "nexus.live.enabled_packs"

  - id: actions
    label: "Actions"
    type: group
    icon: "zap"
    children:
      - id: actions.save-workspace
        label: "Save Workspace"
        type: action
        command: "nexus-ctl workspace save"
      - id: actions.restore-workspace
        label: "Restore Workspace..."
        type: action
        command: "nexus-ctl workspace restore"
      - id: actions.reload-config
        label: "Reload Config"
        type: action
        command: "nexus-ctl config reload"
      - id: actions.scripts
        label: "Scripts"
        type: group
        children:
          # Auto-discovered from .nexus/actions/ and ~/.config/nexus/actions/
          # Enter = run script in new terminal tab
          # Opt+E = open script in editor

  - id: settings
    label: "Settings"
    type: group
    icon: "gear"
    children:
      - id: settings.keymap
        label: "Keybindings"
        type: setting
        config_file: "keymap.conf"
        tags: [keys, bindings, shortcuts]
      - id: settings.theme
        label: "Theme"
        type: setting
        config_file: "theme.yaml"
        tags: [colors, appearance]
      - id: settings.hud
        label: "HUD Modules"
        type: setting
        config_file: "hud.yaml"
        tags: [status, telemetry]
      - id: settings.adapters
        label: "Default Adapters"
        type: setting
        config_file: "adapters.yaml"
        tags: [tools, defaults]
      - id: settings.connectors
        label: "Connectors"
        type: setting
        config_file: "connectors.yaml"
        tags: [wiring, events, automation]
      - id: settings.workspace
        label: "Workspace Config"
        type: setting
        config_file: ".nexus/workspace.yaml"
        tags: [project, workspace]
      - id: settings.tab-bar
        label: "Tab Bar"
        type: setting
        config_file: "tabbar.yaml"
        tags: [tabs, display, pane]

  - id: live
    label: "Live"
    type: group
    icon: "radio"
    children:
      - id: live.tabs
        label: "Active Tabs"
        type: live_source
        resolver: "nexus.live.active_tabs"
        timeout_ms: 1000
      - id: live.processes
        label: "Running Processes"
        type: live_source
        resolver: "nexus.live.processes"
        timeout_ms: 2000
      - id: live.ports
        label: "Open Ports"
        type: live_source
        resolver: "nexus.live.ports"
        timeout_ms: 3000
      - id: live.git
        label: "Git Status"
        type: live_source
        resolver: "nexus.live.git_status"
        timeout_ms: 2000
      - id: live.connectors
        label: "Active Connectors"
        type: live_source
        resolver: "nexus.live.connectors"
        timeout_ms: 1000
      - id: live.agents
        label: "AI Agent Status"
        type: live_source
        resolver: "nexus.live.agent_status"
        timeout_ms: 3000

  - id: custom
    label: "Custom"
    type: group
    icon: "puzzle"
    children:
      # Auto-loaded from menus/ directories (global + workspace)
      # User-defined YAML node trees appear here
```

---

## 7. Dependencies & Infrastructure

### 7.1 Runtime Dependencies

*   **tmux** >= 3.2 (pane-border-format, hooks, display-popup)
*   **Python** >= 3.10 (asyncio, dataclasses, typing)
*   **fzf** >= 0.42 (--bind for Shift+Enter, --preview)
*   **neovim** >= 0.9 (remote RPC, lua API)
*   **zsh** or **bash** >= 5.0

### 7.2 Optional Dependencies

*   **gum** — alternative menu renderer
*   **Textual** — Python TUI menu renderer
*   **yazi** — file explorer adapter
*   **lazygit** — git UI integration
*   **bat** — syntax-highlighted file renderer
*   **opencode** — AI agent adapter

### 7.3 Internal Module Map

```
core/
├── engine/
│   ├── capabilities/          # Registry + adapters (existing)
│   │   ├── registry.py        # CapabilityRegistry (extend with AdapterManifest)
│   │   ├── base.py            # CapabilityType enum + base classes
│   │   └── adapters/          # All adapter implementations
│   ├── orchestration/         # Planner + Executor (existing)
│   ├── state/                 # NexusStateEngine (existing, extend)
│   ├── bus/                   # Event bus (existing)
│   ├── api/                   # nexus-ctl handlers (extend heavily)
│   │   ├── menu_handler.py    # NEW: Command Graph launcher
│   │   ├── capability_launcher.py  # NEW: Alt+o handler
│   │   ├── stack_handler.py   # NEW: Tab stack operations
│   │   ├── tab_manager.py     # NEW: Alt+t handler
│   │   ├── pane_handler.py    # NEW: Alt+q, Alt+v, Alt+s
│   │   ├── switcher.py        # EXISTING: refactor to use new stack model
│   │   └── control_bridge.py  # EXISTING: tool RPC
│   ├── graph/                 # NEW: Command Graph engine
│   │   ├── node.py            # CommandGraphNode model
│   │   ├── resolver.py        # Scope cascade resolution
│   │   ├── loader.py          # YAML → node tree loader
│   │   └── live_sources.py    # Async live source resolvers
│   ├── stacks/                # NEW: Tab stack management
│   │   ├── stack.py           # TabStack + Tab models
│   │   ├── reservoir.py       # Logical reservoir
│   │   ├── manager.py         # Stack lifecycle (create, push, pop, rotate)
│   │   └── tabbar.py          # Pane-border-format renderer
│   ├── packs/                 # NEW: Pack management
│   │   ├── pack.py            # Pack model
│   │   ├── detector.py        # Project marker detection
│   │   ├── manager.py         # Enable/disable lifecycle
│   │   └── registry.py        # Pack registry
│   └── profiles/              # REFACTOR from config/profiles/
│       ├── profile.py         # Profile model
│       └── manager.py         # Profile switching
├── kernel/
│   └── layout/                # Momentum (existing, extend with stack data)
├── ui/
│   ├── compositions/          # Composition JSONs (existing)
│   ├── menus/                 # Menu YAMLs (existing, migrate to Command Graph)
│   └── hud/                   # HUD modules (existing)
└── services/                  # Background services
```

---

**Verification Rule:** Every property (P-01 through P-14) validates at least one Goal ID from the requirements document. Every data model traces to at least one requirement (R-01 through R-57).
