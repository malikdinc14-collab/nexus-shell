# Requirements: Universal Tab Stacks

This document defines the functional and technical requirements for the Universal Tab Stacks system.

## 1. Functional Requirements

### 1.1 Identity-Free Initialization
- **REQ-01**: Every new terminal container (tmux pane, window, etc.) must initialize as an **Anonymous Stack**.
- **REQ-02**: The system must NOT assign a default role (e.g., `editor`) or a physical anchor (e.g., `slot_1`) to a container automatically.
- **REQ-03**: Identities (Roles and Tags) must be **explicitly** assigned by the user via a command or UI action.

### 1.2 Predictable Focus Sovereignty
- **REQ-04**: Tool creation commands (e.g., `Alt-N`) must **always** execute within the container that currently has the user's focus.
- **REQ-05**: If a container has an inherited identity from a parent (e.g., via tmux split), that identity must be ignored or cleared upon interaction if it conflicts with the focus.

### 1.3 Fluid Multi-Role Stacks
- **REQ-06**: A single stack must support multiple tabs running disparate tools (e.g., a mix of shells, vims, and menus).
- **REQ-07**: Users must be able to rotate through the tabs in a stack using consistent keybinds (`Alt-[` and `Alt-]`).

### 1.5 CLI Control
- **REQ-14**: The system must provide a CLI interface (`nxs stack`) for managing stacks and tabs.
- **REQ-15**: The CLI must support the following operations:
  - `push <cmd> [--role <role>]`: Push a new tab to the focused stack (or a specific role).
  - `switch <index>`: Rotate to a specific tab in the focused stack.
  - `close`: Kill the active tab in the focused stack.
  - `tag <name>`: Assign a tag to the current stack.
  - `identity <role>`: Assign a persistent role to the current stack.

## 2. Technical Requirements

### 2.1 Platform Agnosticism & IPC
- **REQ-10**: The core stack orchestration logic must be decoupled from tmux-specific APIs.
- **REQ-11**: The system must implement a **Global Identity Registry** (managed by the Daemon) that tracks stacks across all connected terminal processes.
- **REQ-12**: Every terminal window must have an **IPC Bridge** (e.g., via unix sockets or named pipes) to report its `FocusState` and `StackID` to the central registry.
- **REQ-13**: The system must support **OSC/Terminal escape sequences** or a lightweight shell-sidecar for managing tool rendering in windows that lack a shared multiplexer.

### 2.2 Persistence (Momentum)
- **REQ-12**: The logical state of all stacks (tab order, roles, active tab) must be persistable to the State Engine.
- **REQ-13**: Restoration must be **Coordinate-Aware**: physical panes are mapped to logical stacks based on their screen position, not persistent physical IDs.

## 3. Boundary Conditions
- **BND-01**: Splitting a pane creates a new, independent stack. It does NOT clone the stack of the parent.
- **BND-02**: Closing the last tab in a stack should return the container to an anonymous terminal state rather than destroying the container (unless explicitly configured).
