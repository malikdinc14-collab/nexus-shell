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
- `:debug stop` : Terminate the background debugger.
- `:theme <theme>` : Switch between `nord`, `dracula`, or `gruvbox`.

## 🚨 Automated Features

1. **Conflict Matrix**: If a Git merge fails, Nexus will automatically lock the HUD to `RED ALERT` and force a 3-way split layout for resolution.
2. **Status HUD**: The bottom bar shows your Workspace name, Learner Level (Ascent), Git Branch, and Agent State in real-time.
3. **Headless LSPs**: Language servers run in the background; you just type, and they provide instant feedback.

## 📖 Access & Help
For a full list of commands and modules, open the menu and navigate to **Help** or use the `:help` command.
