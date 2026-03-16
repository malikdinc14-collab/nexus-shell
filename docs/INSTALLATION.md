# Installation Guide 🛠️

Nexus Shell is designed to be portable and isolated. You can install it on macOS (MacBook/iMac) or Linux (including the uConsole).

## 1. Quick Install (Scripted)

The fastest way to get Nexus up and running is using the provided install script:

```bash
# Clone the repository
git clone https://github.com/samir-alsayad/nexus-shell.git
cd nexus-shell

# Run the local installer
./install_local.sh
```

## 2. Manual Prerequisites

Nexus relies on a suite of high-performance CLI tools. Ensure the following are installed via `brew` or `apt`:

- **Tmux** (The Orchestration Engine)
- **Fzf** (Fuzzy Finder)
- **Ripgrep (rg)** (Fast Search)
- **Fd** (File Discovery)
- **JQ & YQ** (JSON/YAML processing)
- **Neovim** (The Core Editor)

## 3. Post-Installation

Once installed, you can launch Nexus by calling the `nxs` binary (added to your PATH by the installer):

```bash
nxs
```

## 4. Tooling Strategy: System vs. Isolated

Nexus uses a dual-path execution strategy for its modular workstation:

- **System Tools (Global)**: By default, Nexus checks your system `PATH`. If you have `lazygit` or `btop` installed via `brew`, Nexus will use them.
- **Isolated Modules (Local)**: For specialized creative tools or custom AI dispatchers, Nexus can use "Internal" versions located in the `services/` or `lib/` directories. 
- **Portability**: This allows you to have a production-grade IDE on your MacBook while maintaining a lightweight, self-contained set of scripts on the **uConsole**.

## 5. Hardware Optimization

### MacBook & Desktop
For maximum performance, ensure `iTerm2` or `Ghostty` is used. Nexus leverages Ghostty's GPU-native features for future rich-media rendering.

### uConsole
If you are running on the **uConsole**, Nexus will auto-detect the terminal dimensions. A minimum of 80x24 is recommended for the specialized creative compositions.
