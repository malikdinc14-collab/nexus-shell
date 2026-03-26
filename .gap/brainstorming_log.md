# Nexus Shell: Workspace OS Brainstorming

## The Vision
Nexus is not just an IDE; it is a **compositional environment** for thought and execution. It is an "OS" in the sense that it manages resources (Capabilities), state (Workspaces), and communication (Bus) across multiple surfaces.

---

## 1. Unified Knowledge Layer ("The Web")
- **Concept**: Instead of separate "Notes" and "Code" nodes, every capability contributes to a shared local Knowledge Graph.
- **Implementation**: A background `KnowledgeCapability` that vectorizes everything as you type/browse.
- **OS Utility**: The "System Search" (Command Palette) doesn't just find files; it finds *concepts* across your browser tabs, notes, and codebases.

## 2. Contextual Identity ("Moods/Modes")
- **Concept**: The workspace reconfigures based on what you are doing.
- **Implementation**: "Context Stakes" - if I'm in "Focus Mode", the HUD hides non-essential telemetry and the Browser capability auto-blocks distracting domains.
- **OS Utility**: Deep state persistence. Closing the app and reopening it on a different machine (Tablet/Mobile) resumes the *exact* logical state.

## 3. Pane-to-Pane Protocols ("Inter-Process Communication")
- **Concept**: Panes should "pipe" data to each other.
- **Example**: Drag a URL from the Browser pane into a RichText pane -> The engine auto-downloads a markdown snapshot of that page.
- **Example**: Focus a line of code in the Editor -> The HUD `GitPart` shows the blame for that specific line instantly.

## 4. Autonomous Background Capability ("Daemons")
- **Concept**: Capabilities that don't have a UI pane.
- **Implementation**: A "Security Watcher" that scans your imports for vulnerabilities and pushes a "High Priority" notification to the HUD.
- **OS Utility**: Continuous, silent assistance.

## 5. Universal URI Scheme
- **Concept**: `nexus://` links for everything.
- **Example**: `nexus://workspace/research#pane_1` -> Specific tab in a specific pane.
- **Example**: `nexus://cmd/markdown.save?path=...` -> Executable links.

## 6. Logic: Kernel Service vs. High-Level Capability

### Refined Architecture
- **`AudioService` (The Kernel Layer)**:
  - Lives in `nexus-daemon`.
  - Responsible for **Hardware Ownership** (rodio, cpal).
  - Provides primitives: `play_buffer()`, `record_stream()`.
  - NOT a plugin-based capability; it's a core system utility.
- **`VoiceCapability` (The Logic Layer)**:
  - Plugin-based adapters in `nexus-core`.
  - Implements the "Intelligence": **TTS/STT**.
  - Adapters: `ElevenLabsAdapter`, `WhisperAdapter`.
  - These adapters *call* the `AudioService` via the Engine/Daemon bridge.

## 7. Multi-Modal Notification System ("System Alerts")

### Core Concept
In a Workspace OS, a notification is a **system event** that can be routed to multiple surfaces and modalities. It's not just a UI toast; it's a persistent record with an associated action.

### Architecture
- **`NotificationService` (Daemon)**: The central registry for all active alerts.
- **`Notification` Data Structure**:
  ```json
  {
    "id": "uuid",
    "priority": "low | high | critical",
    "source": "compiler | git | ai",
    "content": "Build failed in module A",
    "action": "nexus://goto/pane_1",
    "expiry": "timeout | manual_dismiss"
  }
  ```

### Delivery Modes
1. **Visual (HUD)**: A dedicated "Alerts" part in the HUD panel for persistent status.
2. **Native (OS)**: Push to macOS/Windows notification centers for away-from-keyboard awareness.
3. **Voice (Audible)**: Critical alerts are read aloud via the `VoiceManager`.
4. **Actionable**: Clicking a notification triggers a `nexus://` URI (e.g., focusing the terminal that failed).

## 8. The Kernel Event Bus

### Concept
Currently, the [EventBus](file:///Users/Shared/Projects/nexus-shell/crates/nexus-engine/src/bus.rs#120-126) lives in the Engine (User-space). To make Nexus a true Workspace OS, we need a **Kernel Bus** in the Daemon.
- **Purpose**: System-level events (Hardware status, Audio playback completion, critical Notifications) should exist even if the UI Engine is reloading or busy.
- **Inter-Process**: The Daemon broadcasts to the Engine, and the Engine broadcasts to the Surface (UI).

---

## 9. Advanced "Workspace OS" Concepts

### A. Session Time-Travel ("State Rewind")
- **Concept**: The [EventBus](file:///Users/Shared/Projects/nexus-shell/crates/nexus-engine/src/bus.rs#120-126) and [LayoutTree](file:///Users/Shared/Projects/nexus-shell/crates/nexus-engine/src/layout.rs#190-196) already track transitions. We could "snap" the entire OS state every 5 minutes.
- **Utility**: "What was I doing 2 hours ago?" Scrub back and the whole workspace (Layout + Open Files + Terminal PWDs) restores to that moment.

### B. Distributed Capability Mirroring
- **Concept**: Run the `nexus-daemon` on a powerful Linux server, and connect multiple surfaces:
  - **Surface 1 (Mac)**: Main Editor + Terminal.
  - **Surface 2 (iPad)**: Persistent HUD + Voice input.
  - **Surface 3 (Phone)**: Quick notifications and "Remote Kill" for long-running builds.

### C. The "Physical Shell" (IoT Integration)
- **Concept**: Connect external hardware (StreamDeck, LIFX, Phillips Hue) to the Kernel Bus.
- **Utility**: `nexus.on("build.fail", (ev) => lights.color("red"))`. Turn your room into a physical HUD.

### D. Autonomous Project Sidecars
- **Concept**: A background agent that lives in a specific workspace `.nexus/agent.js`.
- **Utility**: It can auto-arrange panes based on your "mood" or proactively refactor code in the background without being a "Chat Pane".

## 10. Core IDE Features (The "Engine" layer)

Aside from AI, a world-class IDE Shell needs deep **Semantic Awareness** and **Execution Context**.

### A. Deep LSP Integration (The "Headless" Brain)
- **Concept**: The `nexus-daemon` should host the LSPs (Language Servers) directly.
- **Utility**: Instead of every pane starting its own LSP client, the Kernel manages one `rust-analyzer` instance. Any capability (Editor, Chat, HUD) can query it for symbols, types, or diagnostics.
- **Goal**: Zero-config "Hover" and "Jump-to-def" across any module.

### B. Global Symbol Indexing & Graph
- **Concept**: A background index of every function, trait, and variable in the workspace.
- **Utility**: The HUD can show a "Symbol Map" of your project. "Find where this trait is implemented" works instantly without a text search.

### C. Deep Terminal Scraping ("Contextual CLI")
- **Concept**: The Daemon "listens" to the PTY output.
- **Utility**: If it sees a stack trace or compiler error, it doesn't just print it; it creates a System Notification with a `nexus://` link to the exact line in the Editor. The shell *understands* the output.

### D. File-System Event Streams
- **Concept**: A unified FS-Watcher capability.
- **Utility**: A build starts automatically when you save a [.rs](file:///Users/Shared/Projects/nexus-shell/crates/nexus-core/src/lib.rs) file. The HUD `TestPart` updates in real-time.

---

## 11. The "Unified Spatial Tree" (The Best of Both Worlds)

I've reviewed the current [layout.rs](file:///Users/Shared/Projects/nexus-shell/crates/nexus-engine/src/layout.rs). We actually already have a primitive **Geometry Layer** ([compute_bounds](file:///Users/Shared/Projects/nexus-shell/crates/nexus-engine/src/layout.rs#139-160)), which is used for the current spatial navigation.

To take it to the next level without replacing what works, we should evolve the [LayoutNode](file:///Users/Shared/Projects/nexus-shell/crates/nexus-tauri/ui/src/tauri.ts#14-24) enum:

### The Proposed Model
```rust
pub enum LayoutNode {
    // 1. Existing: Proven shell/tmux splits
    Leaf { id: String },
    Split { direction: Direction, ratio: f64, left: Box<LayoutNode>, right: Box<LayoutNode> },

    // 2. Added: Weighted Grid (T-junctions, non-binary)
    Grid { weights: Vec<f64>, columns: usize, children: Vec<LayoutNode> },

    // 3. Added: Absolute (Floating / Spatial Overlays)
    Absolute { rect: Rect, child: Box<LayoutNode> },
}
```

### Why this "Combination" is better than an "Alternative":
1. **Compatibility**: Your existing [tmux](file:///Users/Shared/Projects/nexus-shell/crates/nexus-tmux/src/lib.rs#38-66) and `i3` logic continues to work perfectly.
2. **Infinite Flexibility**: You can have a `Split` tree where one "leaf" is actually an `Absolute` floating window or a [Grid](file:///Users/Shared/Projects/nexus-shell/crates/nexus-tauri/ui/src/components/MenuTauri.tsx#303-351) of HUD gauges.
3. **Ray-Casting Navigation**: Since all variants eventually compute to a [Rect](file:///Users/Shared/Projects/nexus-shell/crates/nexus-engine/src/layout.rs#32-38), the navigation logic doesn't care if a pane was created via a Split or a Grid.

### Roadmap for this Model:
1. **Phase 1**: Update the [LayoutNode](file:///Users/Shared/Projects/nexus-shell/crates/nexus-tauri/ui/src/tauri.ts#14-24) enum and adjust [compute_bounds](file:///Users/Shared/Projects/nexus-shell/crates/nexus-engine/src/layout.rs#139-160) to calculate rects for the new variants.
2. **Phase 2**: Implement the [Grid](file:///Users/Shared/Projects/nexus-shell/crates/nexus-tauri/ui/src/components/MenuTauri.tsx#303-351) and `Absolute` insertion commands in [dispatch.rs](file:///Users/Shared/Projects/nexus-shell/crates/nexus-engine/src/dispatch.rs).
3. **Phase 3**: Update the Tauri Surface to render these new spatial layouts.

**Does this "Unified" approach feel like the right balance of innovation and stability?**
3. **Actionable Terminal**: Turning CLI output into engine events.

---

## The "IDE Kernel" Roadmap
1. **LSP Protocol Bridge**: Get the Daemon talking to `rust-analyzer`.
2. **Global Symbol Cache**: Indexing symbols into a queryable engine state.
3. **Actionable Terminal**: Turning CLI output into engine events.
