# The Philosophy of the Dumb Menu
**Date:** March 3rd, 2026
**Context:** Redefining the relationship between Nexus-Shell and Parallax.

## 1. The Historical Mistake
Parallax was originally created as a "control center" that managed its own execution shells. It used complex, bi-directional signal syncing between a "UI shell" and an "Output shell" (e.g. `px-link`, `shell-$$`, etc.). It also launched its own internal Tmux sessions to isolate its environment (`env -u ... tmux new-session...`).

This was an overreach. **Nothing that doesn't *have* to be in Parallax should be in it.**

## 2. The New Paradigm

### 🧠 Nexus-Shell (The Orchestrator)
- **Tmux Master:** Nexus is the single entity allowed to spawn, name, and manage Tmux sessions.
- **Layout Composer:** If you want a layout with a Parallax menu and a bash prompt next to it, Nexus creates that split via a Composition (e.g., `vscodelike`).
- **Data Source:** Nexus is responsible for parsing `.nexus.yaml` and gathering all the actionable data for a workspace.

### 🖼️ Parallax (The Dumb UI)
- **FZF Renderer:** Parallax is simply a beautiful rendering engine for nested lists (Actions, Places, Notes, Models, etc.).
- **No Tmux:** It should run seamlessly inside whatever pane Nexus puts it in. No internal tmux spawning.
- **Dumb Execution:** When a user selects an item in Parallax and hits Enter, Parallax doesn't run it through a complex IPC link. It asks Nexus to run it, or it simply runs the command natively in its current environment, trusting Nexus to route it correctly.

## 3. The Path Forward
To implement this, we must:
1.  **Gut `bin/parallax`**: Remove the 100+ lines of Tmux detachment and environment scrubbing. Parallax should just launch `session.py` immediately.
2.  **Gut the Links**: Delete `px-link` and the `shell-*.link` signal architecture. The UI shell shouldn't be remote-controlling another shell via file watching.
3.  **Refactor Execution**: Actions triggered in Parallax should either execute in the same window (and pause the UI), or tell Nexus to spawn them in a new window/pane.
