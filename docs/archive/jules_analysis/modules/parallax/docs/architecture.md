# Parallax V3 Architecture 🏛️

## 🧠 The Kernel: `px-engine`
At the heart of Parallax is `px-engine`, a stateless, context-aware Python executable.
- **Role**: It accepts a Context (e.g., "actions", "docs") and returns a stream of formatted items.
- **Design**: Zero-dependency (mostly), fast startup.
- **Inheritance**: It resolves configs from `Global (~/.parallax)` -> `Project (.parallax/)` -> `Registry (Stealth)`.

## 📜 Invariant-Driven Design
V3 is built on **Invariants**—truths that must always be maintained.

### 1. The Persistence Invariant
> "The Stage must survive the Dashboard."
- We do not kill the session to exit. We allow the Dashboard pane to die naturally.
- The Stage pane (Shell) is the **Negative Space** that defines the Dashboard.

### 2. The Re-Entry Invariant
> "Parallax must never nest itself destructively."
- If run inside Tmux, Parallax detects it.
- It splits the window, spawns the Dashboard, and exits the foreground process.

## 🔁 The Driver Loop: `bin/parallax`
The shell script that drives the UI.
1.  **Sources Config**: `~/.parallax/config`.
2.  **Resolves State**: Sets up `PX_CTX_FILE`, `PX_NAV_STACK`.
3.  **Hot-Reload Loop**: Wraps FZF in a `while` loop.
    - If a restart flag appears (`/tmp/px-restart...`), the loop continues, reloading config and FZF args.
    - Enables live Layout Swapping (Classic <-> Reverse).

## 🔌 `px-exec`
The clean execution wrapper.
- Instead of messy shell injection (`source ... && eval ...`), we call `px-exec`.
- Usage: `px-exec [SESSION_ID] "command"`
- Handles logging, param loading, and execution in one binary.
