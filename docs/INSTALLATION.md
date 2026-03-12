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

## 4. uConsole Specifics
If you are running on the **uConsole**, ensure your screen resolution is set correctly. Nexus will auto-detect the terminal dimensions, but a minimum of 80x24 is recommended for the specialized compositions.
