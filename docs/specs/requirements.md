# Requirements: Nexus-Shell Composable Architecture

## Introduction
Nexus-Shell is evolving from a single-window tmux environment into a multi-window, composable development station. It aims to provide a mouse-free, highly scriptable IDE experience where the user can open multiple "compositions" against the same project state.

## Glossary
- **Composition**: A specific arrangement of panes and modules (e.g., "IDE", "Debugger", "Terminal-Heavy").
- **Module**: A self-contained tool or viewport (e.g., Neovim, Yazi, Parallax, Shell).
- **Workspace**: A project directory with associated configuration and saved compositions.
- **Station**: The global Nexus-Shell environment for a specific user.
- **PTY Handshake**: The process of synchronizing terminal state and layout across multiple tmux sessions.

## Requirements

### Requirement 1: Multi-Window Project Linking
**User Story**: As a user, I want to open multiple terminal windows that point to the same project, so that I can view different aspects (code, logs, UI) simultaneously without context switching.

#### Acceptance Criteria
1. THE System SHALL support multiple concurrent tmux sessions (clients) linked to a single project root.
2. WHEN a second window is opened for the same project, IT SHALL optionally load a different composition than the first.
3. THE System SHALL maintain shared state (e.g., environment variables, active logs) across all windows in a station.

### Requirement 2: Composable Modularity
**User Story**: As a user, I want to define and save my own "compositions" of modules, so that I can tailor my environment to specific tasks like frontend work or server debugging.

#### Acceptance Criteria
1. THE System SHALL allow users to define "Compositions" in YAML or Shell scripts.
2. A Composition SHALL be able to include any available Module (Editor, Files, Chat, Parallax, Shell).
3. THE System SHALL allow overriding the default composition on a per-workspace basis.
4. THE System SHALL support hot-reloading of layouts.

### Requirement 3: Tabbed Module Interfaces
**User Story**: As a user, I want tabs within my modules (like the shell or parallax), so that I can manage multiple related tasks within a single pane.

#### Acceptance Criteria
1. THE Shell Module SHALL support internal tabs (built on tmux window management or sub-sessions).
2. THE Parallax Module SHALL support tabbed dashboards for different agent activities.
3. THE Editor Module (Neovim/Micro) SHALL integrate its own tabbed system into the Nexus command dispatch.

### Requirement 4: Mouse-Free Navigation
**User Story**: As a user, I want to navigate every window, pane, and tab without touching my mouse, so that I can maintain maximum flow and speed.

#### Acceptance Criteria
1. THE System SHALL provide consistent keybindings for switching between Windows, Panes, and Tabs.
2. THE System SHALL implement a "Command Palette" (dispatch.sh) accessible from any pane.
3. EVERY interactive operation SHALL be scriptable via a CLI command.

### Requirement 5: Persistent Workspace Configuration
**User Story**: As a user, I want my preferred compositions and tool settings to be saved per project, so that I don't have to re-configure my environment every time I switch projects.

#### Acceptance Criteria
1. THE System SHALL look for a `.nexus/` directory in the project root for local overrides.
2. THE System SHALL allow saving a "Current State" into a workspace configuration file.
3. WHEN a project is reopened, THE System SHALL restore the last used composition (or a default specified in `.nexus/`).

### Requirement 6: Future-Proof Visualization (Graph Mode)
**User Story**: As a developer, I want a way to visualize my code as a graph (like Antigravity), so that I can understand complex relationships more intuitively.

#### Acceptance Criteria (Future)
1. THE Architecture SHALL remain flexible enough to integrate a "Graph Module" (potentially using iTerm's image protocols or external windows).
2. THE System SHALL support a "headless" state where a GUI client can consume the Nexus-Shell data stream.

### Requirement 7: Integrated Agentic Workflow (Kiro Framework)
**User Story**: As a developer, I want Nexus-Shell to natively manage my project's Requirements, Design, and Tasks documents, so that my AI coding sessions are structured, traceable, and consistent with the Kiro framework.

#### Acceptance Criteria
1. THE System SHALL provide a dedicated "Spec Manager" module for interacting with `requirements.md`, `design.md`, and `tasks.md`.
2. THE Spec Manager SHALL support automated generation of implementation plans based on approved designs.
3. THE System SHALL allow linking specific Modules or Code Items to Requirements for traceability.
4. THE System SHALL implement a "Walkthrough Mode" that generates proof-of-work artifacts (like `walkthrough.md`) automatically from completed tasks.
5. THE System SHALL support "Property-Driven Development" (PDD) by generating test templates from properties defined in a `design.md`.

### Requirement 8: Station API (Centralized State Store)
**User Story**: As a user, I want all my Nexus windows to share a "brain," so that an action in one window (like switching a file) is known by all others.

#### Acceptance Criteria
1. THE System SHALL maintain a persistent Key-Value store in `/tmp/nexus_$USER/$PROJECT`.
2. EVERY Module SHALL be able to get/set state via a CLI helper (e.g., `nxs-state get cursor_line`).
3. THE System SHALL synchronize environment variables across all active tmux sessions in a station.

### Requirement 9: Nexus Event Bus
**User Story**: As a user, I want my panes to react automatically to events elsewhere in the system, so that my environment feels alive and reactive.

#### Acceptance Criteria
1. THE System SHALL implement a Unix Socket-based event bus for real-time broadcasts.
2. MODULES SHALL be able to subscribe to specific event types (e.g., `FS_EVENT`, `TEST_EVENT`, `AI_EVENT`).
3. THE System SHALL support automated "Action Chains" (e.g., "On `TEST_FAILED`, notify `AI_CHAT` and highlight code in `EDITOR`").

### Requirement 10: Ghost Observers & Mirroring
**User Story**: As a user, I want windows that "follow" my primary workspace, so that I can have a dedicated "Overview" screen that updates as I code.

#### Acceptance Criteria
1. THE System SHALL support "Follower" windows that mirror the context (active file/line) of a "Leader" window.
2. THE Architecture SHALL support passive visualization modules (e.g., Graph View) that update based on Leader signals.

### Requirement 11: Headless Continuity & Deamonization
**User Story**: As a user, I want my station to stay alive when I close my laptop, so that my background AI tasks (Evolution/Refactoring) continue uninterrupted.

#### Acceptance Criteria
1. THE System SHALL support a background daemon (`nexusd`) to manage Station state independently of terminal attachment.
2. THE System SHALL provide a "Resume" capability that re-attaches compositions to their last known state.

### Requirement 12: Project Structure & Repo Layout (Standardized)
**User Story**: As a developer, I want a strictly organized repository, so that core logic is protected from module bloat and every feature has a predictable home.

#### Acceptance Criteria
1. **The Kernel Invariant**: THE `/core` directory SHALL contain only the absolute minimum logic required to boot the station, manage state, and dispatch events. No module-specific code is allowed in `/core`.
2. **SMIO (Standardized Module Input/Output)**: EVERY module in `/modules` SHALL implement:
   - `install.sh`: Idempotent installation script.
   - `init.zsh`: Environment and alias setup.
   - `manifest.json`: Metadata including `category`, `dependencies`, and `version`.
3. **The User Space**: THE `/bin` directory SHALL only contain symlinks to internal boot scripts, serving as the user-facing interface.
4. **Configuration Hierarchy**: Global defaults SHALL live in `/config`, while project-overrides SHALL live in the workspace root's `.nexus/` folder.
5. **Spec-First Development**: EVERY PR or major change SHALL start with an update to the documents in `/specs` (Kiro Framework).
6. **Stateless Logic**: Scripts SHALL avoid hardcoded paths and instead use the `NEXUS_HOME` and `NEXUS_SCRIPTS` environment variables calculated at boot time.
7. **Clean Root**: THE root directory SHALL be kept clean of utility scripts; all such tools SHALL live in `/lib` or `/internal`.

### Requirement 13: Embedded Tool Mode (Parallax/External Tools)
**User Story**: As a user, I want external tools like Parallax to work seamlessly inside Nexus panes without creating nested sessions or conflicting with Nexus state.

#### Acceptance Criteria
1. External tools SHALL detect when running inside Nexus via `PX_NEXUS_MODE` environment variable.
2. WHEN in Nexus mode, tools SHALL skip session creation and run in "dashboard-only" mode.
3. Tools SHALL NOT delete or modify files in `/tmp/nexus_*` or `/tmp/px-*` that may belong to the parent Nexus session.

### Requirement 14: Pane Lifecycle Management
**User Story**: As a user, I want my panes to survive tool crashes and provide a fallback menu, so that I never have to restart my entire station due to a single tool failure.

#### Acceptance Criteria
1. EVERY pane SHALL be wrapped by `pane_wrapper.sh` which catches tool exits.
2. WHEN a tool exits (normally or via crash), THE wrapper SHALL display a "Hub Menu" allowing the user to select another tool.
3. THE wrapper SHALL log all tool starts and exits to `/tmp/nexus_station.log`.

### Requirement 15: Environment Propagation
**User Story**: As a developer, I want environment variables to be consistently available across all panes and processors, so that tools can be configured uniformly.

#### Acceptance Criteria
1. THE layout engine SHALL explicitly export all tool configuration variables before calling sub-processors.
2. THE tmux session SHALL inherit `NEXUS_HOME`, `NEXUS_CORE`, `WRAPPER`, and tool-specific vars via `tmux set-environment`.
3. Shell variables defined in `launcher.sh` SHALL be accessible in all panes without requiring re-sourcing.
