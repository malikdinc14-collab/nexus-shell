# Nexus Shell

**A modular, high-performance terminal IDE framework built on TMUX.**

Nexus Shell transforms your terminal into a powerhouse IDE. It uses a "Bring Your Own Tools" philosophy—acting as an orchestration engine that perfectly arranges your favorite CLI and TUI applications (like Neovim, Yazi, Lazygit, and AI chats) into indestructible, hot-swappable workspaces.

## ✨ Core Features

*   **Hot-Swappable Compositions:** Switch your entire terminal layout in milliseconds. Go from a standard VSCode-like layout to a dedicated Data Engineering or SRE layout instantly.
*   **Branch-Aware Workspaces:** (New) Nexus auto-saves window geometries based on your current Git branch. Check out a new branch, and your entire IDE layout shape-shifts automatically.
*   **Multi-Window Project Slots:** Open up to 10 independent layout slots in the exact same directory and jump between them instantly using `Alt-1` through `Alt-9`.
*   **Indestructible Panes:** Applications run in isolated, respawnable wrappers. If a tool crashes or you exit it, the pane immediately returns to the Nexus Tools menu—your layout never breaks.
*   **Zero-Config Module Auto-Discovery:** Install a tool via Homebrew/apt, drop a 5-line JSON manifest into `modules/`, and it instantly appears in the UI. No compiling, no restarting.
*   **Spatial Persistence:** Ordered restoration of window geometry across project restarts—Nexus remembers exactly how you left your workstation.
*   **Terminal Viewport:** (New) Built-in terminal-based Chromium browser (Carbonyl) for rendering interactive notebooks, Markdown previews, and documentation.
*   **Deep Nvim Integration:** Built-in RPC allows Nexus bounds to talk directly to your Neovim instance.

---

## 🛡️ Sovereign Infrastructure (New)

*   **Nexus Guard:** A safety airlock for the host. Intercepts destructive commands (rm, git reset) with real-time HUD alerts and project-level whitelisting.
*   **Secure Keychain:** Zero-plaintext secret management. API keys are stored in the macOS Keychain and injected into the environment on boot. No more `.env` files.
*   **GAP Autonomous Bridge:** Direct bridge to the Gated Agent Protocol. Launch autonomous missions in isolated Orbstack VMs with real-time Neovim following.
*   **Spatial Persistence:** Ordered restoration of 10+ window slots. Nexus remembers your entire multi-view cockpit across reboots.

---

## 🚀 Getting Started

Nexus Shell is designed for speed and portability. 

- **Installation**: See [**docs/INSTALLATION.md**](file:///Users/Shared/Projects/nexus-shell/docs/INSTALLATION.md) for quick install and prerequisites.
- **User Guide**: See [**docs/USER_GUIDE.md**](file:///Users/Shared/Projects/nexus-shell/docs/USER_GUIDE.md) for keybinds and commands.
- **Vision**: See [**docs/vision.md**](file:///Users/Shared/Projects/nexus-shell/docs/vision.md) for the "Universal Creative Workstation" philosophy.

```bash
# Quick Launch (after installation)
nxs
```

---

## 🪟 Compositions (Layouts)

Compositions are JSON/YAML files that define how your terminal is split and what tool runs in each pane. Switch them on the fly via the `Compositions` menu or CLI.

**Included Domain Workspaces:**
*   `vscodelike` - The default: File tree, Editor, Terminal, and AI Chat.
*   `ai-pair` - 55% width dedicated to AI chat (Opencode/Aider) for pair programming.
*   `git-review` - Lazygit + GH-Dash PR dashboard for code review.
*   `devops` - Lazydocker + Btop + Editor for cluster management.
*   `data-eng` - Harlequin SQL IDE + Visidata for data exploration.
*   `sre` - Live logs + network bandwidth (Bandwhich) + system monitoring.
*   `music-studio` - Spotify Player + Cava visualizer.
*   `writer` - Distraction-free editor + Glow markdown preview.
*   `network` - Termshark packet capture + Trippy diagnostics.
*   `minimal` - Just an editor and a terminal.

**CLI Usage:**
```bash
nxs -c devops      # Launch directly into the DevOps layout
nxs -c ai-pair     # Launch directly into the AI layout
```

---

## ⌨️ Keybinds & Controls

Nexus Shell uses **`Alt` (Option on Mac)** for pane navigation and global actions, and **`Ctrl+\`** for the command prompt.

### Global Actions
| Key | Action |
|-----|--------|
| `Ctrl + \` | Open the Command Prompt (e.g., type `:wq`, `:theme`) |
| `Alt + 1...9`| Jump instantly between Window Slots 1-9 |
| `Alt + X` | Escape to Menu (Kills current tool, opens Nexus Menu) |
| `Alt + P` | Focus Menu Pane |
| `Alt + F` | Project Search (fd + fzf) → Opens in Nvim |
| `Alt + Shift + F` | Live Grep (ripgrep) → Opens in Nvim |
| `Alt + Shift + G`| Toggle File Tree |
| `Alt + G` | Open Git (Lazygit) in popup |
| `Alt + I` | Send Nvim Context to AI Chat |
| `Alt + Shift + I`| Send Terminal Error to AI Chat |

### Navigation (Normal Mode)
Press `Alt + Escape` to enter Normal mode (hide the UI for deep focus), then:
| Key | Action |
|-----|--------|
| `n` | Focus File Tree |
| `e` | Focus Editor |
| `t` | Focus Terminal |
| `c` | Focus Chat |
| `Esc` | Return to Insert mode |

---

## 💬 Command Prompt registry

Press `Ctrl+\` to open the prompt, then type:

| Command | Description |
|---------|-------------|
| `:save` | Snapshots the current tmux layout and saves it manually |
| `:wq` | Saves layout for current window, and closes the current window |
| `:wqa` | Saves layouts for all open windows, and shuts down the entire session |
| `:q` | Graceful shutdown of the current window only |
| `:qa` | Graceful shutdown of the entire session (all slots) |
| `:theme` | Open the Theme Picker (Cyber, Dark, Light) |
| `:settings`| Open the Configuration Menu |
| `:tools` | Open the Installed Tools Menu |
| `:run` | Execute a task defined in `.nexus.yaml` |
| `:build` | Shortcut for `:run build` |
| `:test` | Shortcut for `:run test` |
| `:web` | Open a terminal-based web view (Carbonyl/Grip) |
| `:help` | Show the comprehensive help popup |

---

## 🔧 Modules (Bring Your Own Tools)

Nexus currently ships with manifests for **34 popular TUIs**.

If you have the tool installed on your system (e.g., `brew install btop`), Nexus will automatically detect it and enable it in your `Alt-X -> Tools` menu. If you don't have it, clicking it will tell you exactly how to install it.

### Adding a Custom Tool
Nexus doesn't use a package manager. Adding a custom tool takes 10 seconds.

**1. Create a folder:**
```bash
mkdir -p modules/my-tool
```

**2. Create a `manifest.json`:**
```json
{
    "name": "My Awesome Tool",
    "description": "Does something cool",
    "command": "my_cli_command --flag",
    "category": "productivity"
}
```
*That's it.* It will instantly appear in the Nexus UI, fully integrated.

---

## 🎨 Themes

Themes are managed via simple YAML files in `config/themes/`. Switching a theme inside Nexus automatically updates the TMUX status bar, borders, popups, and sends an RPC call to Neovim to change its colorscheme and background simultaneously.

Available by default: `cyber` (Cyan/Neon), `dark` (Catppuccin Mocha), `light` (Catppuccin Latte).

---

## 🏗️ Architecture Stack

*   **Multiplexer:** `tmux` (Handles the window geometry and layout saving)
*   **Menu Engine:** Custom Python engine wrapping `fzf`
*   **Editor RPC:** `nvim --listen` + `nvim --server`
*   **Search Engine:** `ripgrep`, `fd`, `fzf`, `bat`
*   **Core Shell:** `zsh` / `bash` 

## License
MIT
