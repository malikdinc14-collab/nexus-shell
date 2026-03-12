# Nexus-Shell & Parallax: The Terminal IDE You Actually Want

Transform your terminal into a powerhouse. **Nexus-Shell** is a modular, high-performance terminal IDE built on TMUX, powered by the **Parallax** automation engine. 

![Nexus-Shell Preview](https://github.com/samir-alsayad/nexus-shell/raw/main/preview.png)

## 🌌 Nexus-Shell: The Interface
Nexus-Shell isn't just a config; it's a carefully crafted environment that bridges the gap between terminal speed and modern IDE features.

- **Persistent Workflow**: Panes are "indestructible." Tools exit gracefully into a hub menu, meaning you never lose your layout to a simple `exit` or crash.
- **Deep Integration**: Seamlessly bridge your tools. Type `edit file.rs` in the terminal to jump to Neovim, or `view readme.md` for a rich markdown preview.
- **Total Modularity**: Bring your own tools or let Nexus manage isolated versions of Neovim, Yazi, and Glow for you.
- **Cyberpunk Aesthetics**: Curated themes like `nexus-cyber`, `ghost-noir`, and `the-void` make your development environment look as sharp as it feels.

## ⚙️ Parallax: The Engine
Under the hood, **Parallax** manages the complexity of your shell sessions and workflow automation.

- **Signal-Based IPC**: Real-time synchronization between shell sessions using Unix signals (SIGUSR1/SIGUSR2).
- **Interactive TUI Dashboard**: A lightning-fast FZF-powered interface to trigger custom actions, manage environments, and switch project contexts.
- **Workflow Actions**: Turn any script into a first-class dashboard tool with simple metadata annotations.

---

## 🚀 Quick Start

Get the full experience in seconds:

```bash
git clone --recursive https://github.com/samir-alsayad/nexus-shell.git
cd nexus-shell
./install.sh
```

Then, just run:
```bash
nxs
```

## 🛠 Tech Stack
- **Engine**: Parallax (Zsh + Python)
- **Multiplexer**: TMUX
- **Editor**: Neovim (with RPC integration)
- **Navigator**: Yazi
- **CLI Helpers**: FZF, Gum, Glow

---

### 📦 Pre-Push Checklist (99% → 100%)
Since your newest release is nearly perfect, here are a few things to check before hitting that `git push`:

1.  **Submodule Sync**: Ensure the `modules/parallax` submodule is pointing to the correct commit.
2.  **Isolated Configs**: Verify that the tool configs in `config/` are properly copied to `~/.config/nexus-shell` during installation.
3.  **Theme Check**: Test the `:theme` command one last time to ensure all JSON definitions are valid.
4.  **Installer Cleanliness**: Run `./uninstall.sh` and then `./install.sh` to ensure the "first-run" experience is flawless.

**Ready to deploy? Let's take the terminal to 2077.**
