# VISION: Nexus Shell — The Multimodal Creative Workstation 🌌

## 1. The Core Philosophy: "The Universal Creative Engine"
Nexus Shell is not just a terminal multiplexer or an IDE; it is a **Multimodal Creative Workstation**. Inspired by the Digital Audio Workstation (DAW) model, it is designed for **Computational Creativity**—whether that is composing music through code, researching AI architectures on a MacBook, or managing a field-deployed uConsole.

## 2. Decoupled Intelligence (Modular HUDs)
The HUD is not a fixed bar. It is a **Dynamic Telemetry Strip**.
- **Music Studio**: The HUD shows BPM, active MIDI channels, and CPU load.
- **Writer Workspace**: The HUD shows word count and focus time. AI is disabled.
- **Ascent Workspace**: The HUD shows Learner Level, XP, and active curricula.
- **Research Workspace**: The HUD shows GPU utilization, model latency, and dataset progress.

## 3. Compositions as Definitions
A **Composition** (`compositions/*.json`) is the "Project File" of Nexus. It defines:
- **Topology**: The Tmux pane layout.
- **Service Set**: Which background daemons run (LSPs, DAPs, Aggregators).
- **HUD Provider**: Which script renders the status bar.
- **Keybind Overlay**: Domain-specific hotkeys (e.g., `Alt-s` for "Submit" in one, "Search" in another).

## 4. The "Pure Modularity" Target
We move away from "Global Features" toward "Domain Modules". 
- **Core**: Tmux, Session Management, Router, GAP.
- **Extensions**: Ascent, Music-DSP, Research-Ops, Diagnostics.
- **UI Renderers**: Ghostty-native Markdown rendering, TUI visualization layers.
- **Profiles**: The logic that binds Extensions to the Core for a specific mission.

## 5. Summary
Nexus Shell is the substrate. The **Workspace** is the specialized tool. The user does not "use Nexus"; they "load the specialized factory" for the mission at hand.
