# Nexus-Shell Architecture & Forensics

This document provides a transparent map of the Nexus-Shell environment, its recent failures, and the path to a stable, production-ready state.

## 1. System Map (The File Tree)

Nexus-Shell is designed to exist in two distinct "states": **Source** and **Installation**.

### Source Repository (`~/Projects/personal/nexus-shell/`)
- This is where you code.
- Contains the `.git` history and the `install.sh` / `install_local.sh` scripts.
- **core/kernel/boot/**: The core logic (Launcher, Architect, Wrapper).
- **modules/parallax/**: The submodule for state synchronization.

### Live Installation (`~/.config/nexus-shell/`)
- This is the "Stable Snapshot" used by your terminal.
- It is decoupled from the Source to prevent developmental bugs from crashing your active station.
- **core/kernel/boot/**: Physical copies of the source scripts.
- **tmux/nexus.conf**: The hardened TMUX configuration.

---

## 2. Forensic Analysis: The Three Faults

We have identified why the recent attempts to "improve" the station resulted in a "Process Bomb" and "Silent Crashes."

### Fault 1: Identity Contamination
- **Symptom**: Your native terminal window thinks it's a Nexus pane.
- **Cause**: `~/.nexus-shell.zsh` was being sourced globally in your `~/.zshrc`, exporting `NEXUS_` variables to every shell.
- **Fix**: The "Identity Firewall." Variables and hooks now only activate if the shell detects it is inside a TMUX session named `nexus_*`.

### Fault 2: The Path Schism
- **Symptom**: `zsh: no such file or directory: /Users/samir/bin/layout_engine.sh`
- **Cause**: The `nxs` command in `~/bin/` is a symlink. When the script ran `dirname $0`, it pointed to `~/bin/` instead of the actual script directory in `.config/`.
- **Fix**: Physical Path Resolution. Scripts now follow their own symlinks to find their "real" home before looking for helper files.

### Fault 3: The Zero-Point Failure (TMUX Death)
- **Symptom**: `[server exited]` and `no server running`.
- **Cause**: Attempting to run `tmux start-server` or `tmux set-option` *before* a session exists. On macOS, the server often exits if it has no active session to manage.
- **Fix**: "Session-First" logic. The first command must be `new-session`, which forces the server to stay alive.

---

## 3. The "Negative Space" Invariants

To prevent the **Process Bomb** from returning, we have enforced four mathematical invariants:

1.  **TTY Invariant**: Interactive panes MUST have a terminal context. If not, they idle safely instead of spinning crashing shells.
2.  **Parentage Invariant**: When a pane wrapper exits, it explicitly kills all its child processes (`pkill -P $$`), preventing orphans.
3.  **Singleton Invariant**: Only one background monitor can exist per project.
4.  **Terminal Lifecycle Invariant (Negative Space)**: A Nexus session MUST NOT exist without an active observer (terminal window). Closing the window or detaching physically destroys the session and all its children.

---

## 4. Operational Comparison

| Feature | Old implementation (Shared) | Current Implementation (.config) |
| :--- | :--- | :--- |
| **Stability** | High (Simple, direct session creation) | Low (Over-engineered server initialization) |
| **Isolation** | None (Contaminates native terminal) | High (Firewalled environment) |
| **Pathing** | Fragile (Relative to $CWD) | Robust (Absolute via Symlink resolution) |
| **Recovery** | Manual `pkill` | Atomic `nxs-kill` (nxxx) |

---

## 5. Recovery Procedures

### The "Total Purge" (`nxxx`)
If the system becomes unstable, run `nxxx` in any terminal. It will:
1. Kill the `tmux` server.
2. Purge all `nexus`, `parallax`, and `opencode` orphans.
3. Reset the internal state.

### The "Local Install"
After making changes in your `Projects/` folder, run:
```bash
cd ~/Projects/personal/nexus-shell && ./install_local.sh
```
This pushes your code to the live station in `~/.config/`.
