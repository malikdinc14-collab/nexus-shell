# Technical Design: Nexus Pilot Monitor (Phase 2)

**Status**: Draft for Implementation
**Objective**: Provide a native, high-fidelity process management interface for the human pilot.

---

## 1. The "IDE Context" Advantage
Standard tools like `htop` or generic plugins don't know about Nexus. The Pilot Monitor will:
- **Map Tabs to Processes**: Show which "Nexus Tab" (e.g., "zsh", "ls-monitor") owns which process tree.
- **Resource Warnings**: If a background tab spikes to 100% CPU, the Pilot Monitor publishes an event to the Status Bar.
- **Hermetic Safety**: Protect core Nexus components (the Parallax daemon, the Event Bus server) from accidental termination.

---

## 2. Global View (`nxs-monitor`)

### UI Model (Floating UI)
- **Invoke**: `Alt + M` (or via Command Palette).
- **Interface**: A centered `tmux display-popup` running a dedicated Python viewer.
- **Layout**:
  ```text
  [ VIEWPORT: TERMINAL ]
  ├─ [Tab 1: zsh] (PID 512) CPU 0.1% MEM 8MB
  │  └─ [npm run dev] (PID 881) CPU 45% MEM 120MB  <-- HIGH USAGE
  └─ [Tab 2: logs] (PID 603) CPU 0.0% MEM 2MB
  ```

### Interactive Actions
- **Select + K**: Kill process.
- **Select + R**: Restart the Tab (Nexus calls `respawn-tab`).
- **Select + Enter**: Swap that Tab into the active viewport immediately.

---

## 3. The "Guardian" (Safety Layer)
The Monitor will include a "Core Protect" list. Attempts to kill these will require a double-confirmation:
- `px-bus` (Event Bus)
- `parallax-daemon` (The Brain)
- `nexus-launcher` (The Station)

---

## 4. Feature Roadmap
1. **Tree View**: Visualize the relationship between the Shell and the tasks it running.
2. **Tab Association**: Every process row prefixed with its Tab title from `tabs.json`.
3. **Signal Support**: Send `HUP`, `TERM`, or `KILL` directly.
