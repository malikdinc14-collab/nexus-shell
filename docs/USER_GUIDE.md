# Nexus Shell: The Definitive User Guide 📕

Welcome to the Factory. Nexus Shell is a high-performance development environment designed for speed, isolation, and AI orchestration.

## ⌨️ Global Keybinds (The Muscle Memory)

| Key | Action | Description |
| :--- | :--- | :--- |
| **Alt-x** | **The Menu** | Open/Close the Parallax Command Menu. |
| **Alt-f** | **Quick Find** | Fuzzy search for files across all workspace roots. |
| **Alt-F** | **Live Grep** | Search for text inside every file in the workspace. |
| **Alt-j** | **Global Jump** | Jump to code from any stack trace (Editor navigation). |
| **Alt-g** | **Lazygit** | Pop up a full Git TUI for staging and commits. |
| **Alt-i** | **Context Pump** | Send current buffer/terminal context to the AI (Agents). |
| **Alt-I** | **Error Pipe** | Send the last terminal error to the AI for diagnosis. |
| **Alt-1..9** | **Fast Pane** | Instantly focus Workspace panes or Slots (9 = Debug Console). |
| **Alt-[ / ]** | **Tabs** | Navigate through terminal tabs within the active pane. |

## 🛠️ Specialized Commands

Enter these in the Parallax Menu (`Alt-x`):

### Workspace & Profiles
- `:workspace <path>` : Load a new project or multi-folder workspace.
- `:profile <name>` : Hot-swap your environment (e.g., `focus`, `swarm`, `ascent`).
- `:composition <name>` : Switch layouts (e.g., `vscodelike`, `ascent`, `writer`).

### Intelligence & Debugging
- `:debug start <file>` : Launch a headless background debugger (Python/Node).
- `:debug attach` : Switch view to the active debug console.

## 🚨 Automated Features

1. **Conflict Matrix**: If a Git merge fails, Nexus will automatically lock the HUD to `RED ALERT` and force a 3-way split layout for resolution.
2. **Modular HUD**: The bottom bar is profile-aware. It shows Workspace name and status, but adapts to show domain-specific data (like Learner Level in Ascent) only when that profile is active.

## 📄 Further Reading
- [**Vision: The Composable Engine**](file:///Users/Shared/Projects/nexus-shell/docs/vision.md)
