# Nexus Shell Taxonomy

This document defines the official terminology for the Nexus navigation system.

## 1. Physical Layer (Renderers)
- **Container**: Any physical area that can render a Nexus Stack.
  - **Pane**: A physical box within a tmux window.
  - **Window**: A standalone terminal emulator window (e.g., iTerm2, Alacritty).
- **Container ID**: A transient identifier for a physical container (e.g., `tmux:%14` or `window:567`).

## 2. Logical Layer (Architecture)
- **Stack**: A logical collection of **Tabs**. It is the unit of work.
- **Stack ID**: A persistent UUID for a stack.
- **Tab**: A single process or tool (e.g., nvim, zsh, menu) running within a stack.
- **Active Tab**: The tab currently being rendered in the stack's container.
- **Background Tab**: A tab that exists in a stack but is currently hidden/reservoired.

## 3. Modular Identity (Capabilities)
- **Capability (Module)**: A high-level semantic function required by the user (e.g., `editor`, `chat`, `explorer`).
- **Extension (Tool)**: The specific software implementing a capability (e.g., `nvim`, `claude_code`, `yazi`). 
- **Adapter**: Metadata and logic that bridges a Capability to an Extension (e.g., `NvimAdapter`).
- **Role**: A user-facing alias for a Stack, usually mapping 1:1 to a Capability (e.g., "The Editor Stack"). Exactly one "Active" stack exists for each role globally.

## 4. Metadata & Orchestration
- **Tag**: Metadata assigned to a stack for grouping or searching (e.g., `feature-A`, `legacy`).
- **Anchor**: The last known physical position (proportional coordinates) of a stack.
- **Logical Multiplexing**: Managing focus and tab-swapping across multiple physical containers.
- **Registry**: The central state store (managed by the Daemon) that identifies and tracks all Stacks.

## 5. Axiomatic Invariants
- **Identity-First**: Operations must use semantic IDs (UUID, Role, Tag), never physical indices.
- **Contextual Portal**: Navigation (Alt+X) must resolve the most relevant Stack for the current focus.
- **Geometric Continuity**: A stack must maintain its proportions even when swapped or backgrounded.
