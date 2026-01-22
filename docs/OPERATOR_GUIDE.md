# 🎮 Nexus Intelligence OS: Keybindings & Operator Guide

Welcome to your upgraded development environment. This guide covers the navigation, orchestration, and intelligence commands for the Nexus-Shell / Parallax "Intelligence OS".

---

## 🧭 Global Navigation (Layout Tabs)
Nexus is organized into specialized windows (tabs). Switch between them instantly using **Alt + Key**.

| Key | Window | Purpose |
| :--- | :--- | :--- |
| **`Alt + O`** | **Workspace** | Primary coding environment (Editor, Chat, Tree). |
| **`Alt + W`** | **Workflow** | Planning Mode (Requirements -> Design -> Tasks). |
| **`Alt + M`** | **Monitor** | Hardware telemetry, Agent Trace logs, Task status. |
| **`Alt + S`** | **Shells** | Quad-split interactive terminals for manual work. |

---

## 🖥️ Pane & Tab Management
Control the individual areas within a window.

### **Focus & Resizing**
- **`Alt + h/j/k/l`**: Move focus between panes (Vim-style).
- **`Alt + Arrows`**: Move focus between panes.
- **`Alt + Esc`**: Enter **NORMAL MODE**. In this mode:
    - `h/j/k/l` moves focus.
    - `H/J/K/L` (Shift) resizes the current pane.
    - `Enter` returns to **INSERT MODE**.

### **Terminal Area Tabs (Bottom Pane)**
Manage multiple shells within the bottom terminal area.
- **`Alt + =`**: Create a **New Terminal Tab** (Shell).
- **`Alt + ]`**: Switch to **Next** Terminal Tab.
- **`Alt + [`**: Switch to **Previous** Terminal Tab.

---

## 🧠 Intelligence & Command Control
The global command prompt is your entry point for all actions.

### **The Command Prompt (`Ctrl + \`)**
Press **`Ctrl + \`** to open the prompt at the bottom of your screen.

| Command | Action |
| :--- | :--- |
| **`! [query]`** | Send a direct request to the **Ghost Operator**. |
| **`:spawn [idx]`**| Open a **new OS window** for the specified layout index (0-3). |
| **`:kill`** | Immediately terminate all active background agents. |
| **`:down`** | **Unload all models** and shut down local backends (reclaim RAM). |
| **`:q`** | Safe Exit (Nexus will ask if you want to unload models). |
| **`:q!`** | Force Exit (Immediate shutdown of everything). |

---

## 🏗️ The RDT Workflow (Planning Mode)
Located in the **Workflow (`Alt + W`)** tab.

1.  **Browse**: Use the Parallax dashboard to navigate Requirements, Designs, and Tasks.
2.  **Preview**: Selecting a file shows it in the center Render pane (supports Mermaid).
3.  **Cross-Link**: Every file lists its interlinks (e.g., `📄 REQ-001 🔗 DSN-001`).
4.  **Edit**: Select a document and choose **`↳ 📝 Open as Editor Tab`** to open that plan directly inside your Neovim instance in the primary Workspace.

---

## 🛡️ Safety & Telemetry
Keep your 48GB Mac stable during stress tests.

- **`Alt + M`**: Monitor your **GPU Load** and **RAM Pressure** in real-time.
- **Resource Guard**: Located in `Brains > 🛡️ Resource Guard`. When ON, it will automatically trigger a `:down` if RAM usage exceeds **44GB** to prevent a system freeze.
- **Agent Trace**: Watch the `Trace` pane in the Monitor window to see the agent's raw logic and tool-call metadata.

---

## 🔬 LLM-Lab Special Actions
When working in `~/Projects/llm-lab`, use these custom dashboard actions:
- **🧪 Benchmark RLM**: Run the 1-layer recursive inference benchmark.
- **🧬 Run Engram Demo**: Execute the DeepSeek Engram lookup logic test.
- **🧠 Test AgentCPM**: Start a chat session with the lightweight Scout model.

---

**Tip**: Use `:help` in the command prompt or press `^H` in the Parallax Dashboard for contextual help at any time.
