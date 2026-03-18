# Design: Universal Tab Stacks Architecture

## 1. System Components

### 1.1 The Logical Multiplexer (Daemon)
The Nexus Daemon (`nxs-d`) acts as the source of truth for all stacks.
- **Global Stack Registry**: A memory-mapped dictionary of all active stacks.
- **State Model**: 
  ```json
  {
    "stacks": {
      "UUID-123": {
        "tabs": [{"id": "%pane_1", "role": "editor", "name": "nvim"}],
        "active_index": 0,
        "tags": ["work", "primary"]
      }
    },
    "containers": {
      "tmux:%1": "UUID-123",
      "window:567": "UUID-456"
    }
  }
  ```

### 1.2 The Platform Adapter (ABC)
To achieve platform-agnosticism, Nexus uses the **Adapter Pattern**. The Daemon interacts with containers via a unified interface:

- **`BaseContainerAdapter` (ABC)**:
  - `identify_current_container() -> container_id`
  - `split_container(direction) -> new_container_id`
  - `render_stack(stack_id, container_id)`
  - `get_geometry(container_id) -> ProportionalRect`

- **`TmuxAdapter` (Implementation)**:
  - Uses `tmux display-message` and `tmux split-window`.
- **`WindowAdapter` (Future Implementation)**:
  - Uses OS-level window management APIs (e.g., AppleScript for iTerm2 or X11/Wayland protocols).

### 1.3 The IPC Bridge
Communication between terminal containers and the Daemon occurs via a **Universal IPC Bridge**.
- **tmux**: Uses the `stack` client as a proxy to the Daemon.
- **Independent Windows**: Use a lightweight shell-sidecar that reports focus change events to the Daemon's socket.

### 1.3 Geometric Presence (The "Anchor")
Instead of physical `@nexus_slot` variables, the system uses **Geometric Anchors**.
- During session saves, the Daemon records the **Screen Proportion** of each stack (e.g., `x:0, y:0.5, w:0.5, h:0.5`).
- On restoration, the Layout Engine spawns containers and the Daemon "pours" the matching stack into the container closest to the saved coordinates.

## 2. The Logical Background (The Reservoir)
Instead of a physical "Reservoir Window," the system manages inactive tabs as a **Logical Background State**.

- **Stack Registry Update**: 
  ```json
  "tabs": [
    {"id": "%pane_1", "status": "VISIBLE"},
    {"id": "%pane_2", "status": "BACKGROUND"}
  ]
  ```

### 2.1 Adapter-Level Implementation
-   **TmuxAdapter**: Implements the background state using a dedicated `RESERVOIR` window and `swap-pane`. This is a physical optimization for tmux.
-   **WindowAdapter**: Implements the background state by **closing/hiding** the terminal window while maintaining the PTY connection in the background. On "Switch," it spawns a new container and reconnects the PTY.

## 3. Key Flows

### 3.1 The "Tab Rotation" Flow (Alt-[ / Alt-])
1. User requests rotation in **Container A**.
2. Daemon identifies the next tab in the stack.
3. Daemon tells the **Platform Adapter**: "Make Tab X visible in Container A, and move Tab Y to the background."
4. The Adapter performs the physical swap or window update.

## 6. Container Lifecycle
The system distinguishes between **Persistent Containers** and **Ephemeral Containers**.

- **Creation**:
  - When a stack with no container is "Activated" (e.g. via CLI or Menu), the Daemon asks the Platform Adapter to create a new container.
  - **Tmux**: Splits a pane or opens a window.
  - **Standalone**: Spawns a new terminal window process.
- **Destruction**:
  - When the last tab in a stack is closed:
    - **Persistent Containers** (User-created splits): Remain as an anonymous shell.
    - **Ephemeral Containers** (System-spawned windows): Are closed automatically to prevent window clutter.

## 7. Data Integrity & Boundary Rules
- **Split Invariance**: A tmux split creates a NEW physical `container_id`. Since the Daemon has no mapping for this new ID, it naturally treats it as an **Anonymous Container**, satisfying the vision of identity-free splits.
- **Window Migration**: A stack can be "detached" from one container and "attached" to another, allowing for fluid multi-window management.
