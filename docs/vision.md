# VISION: Nexus Shell — The Composable Workspace Engine 🌌

## 1. The Core Philosophy: "DAW for Code"
Nexus Shell is not just a terminal multiplexer; it is a **Modular Orchestrator**. Just as a Digital Audio Workstation (DAW) allows a musician to load different plugins, mixers, and instruments depending on the track, Nexus allows a developer to load "Compositions" that redefine the entire environment UI, logic, and telemetry.

## 2. Decoupled Intelligence (Modular HUDs)
The HUD is not a fixed bar. It is a **Dynamic Telemetry Strip**.
- **Writer Workspace**: The HUD shows word count and focus time. AI is disabled.
- **Ascent Workspace**: The HUD shows Learner Level, XP, and active curricula.
- **Research Workspace**: The HUD shows GPU utilization, model latency, and dataset progress.

## 3. Compositions as Definitions
A **Composition** (`compositions/*.json`) is the "Project File" of Nexus. It defines:
- **Topology**: The Tmux pane layout.
- **Service Set**: Which background daemons run (LSPs, DAPs, Aggregators).
- **HUD Provider**: Which script renders the status bar.
- **Keybind Overlay**: Domain-specific hotkeys (e.g., `Alt-s` for "Submit" in one, "Search" in another).

## 4. The "Highly Modular" Target
We move away from "Global Features" toward "Domain Modules". 
- **Core**: Tmux, Session Management, Router, GAP.
- **Extensions**: Ascent, DAP-debug, Diagnostics, Conflict Matrix.
- **Profiles**: The logic that binds Extensions to the Core for a specific task.

## 5. Summary
Nexus Shell is the substrate. The **Workspace** is the specialized tool. The user does not "use Nexus"; they "load the specialized factory" for the mission at hand.
