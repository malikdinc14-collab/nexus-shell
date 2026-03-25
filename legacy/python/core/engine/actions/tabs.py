#!/usr/bin/env python3
"""
Tab Actions
===========
Universal tab engine for window and pane-level tab management.
All multiplexer operations go through the adapter layer.
"""

import sys
import os
from pathlib import Path

_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from engine.actions.resolver import AdapterResolver


def _get_session():
    return os.environ.get("NEXUS_SESSION", "nexus_default")


def nexus_next():
    """Switch to next tmux window (workspace slot)."""
    mux = AdapterResolver.multiplexer()
    mux._run(["select-window", "-t", "+1"])


def nexus_prev():
    """Switch to previous tmux window (workspace slot)."""
    mux = AdapterResolver.multiplexer()
    mux._run(["select-window", "-t", "-1"])


def _get_panes_by_prefix(prefix):
    """Find all panes with titles matching a prefix."""
    mux = AdapterResolver.multiplexer()
    session = _get_session()
    raw = mux._run(["list-panes", "-s", "-t", session, "-F",
                     "#{pane_id} #{pane_title}"])
    if not raw:
        return []
    result = []
    for line in raw.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[1].startswith(prefix):
            result.append((parts[0], parts[1]))
    return sorted(result, key=lambda x: x[1])


def _get_visible_pane(role_prefix):
    """Find the currently visible pane for a role/prefix."""
    mux = AdapterResolver.multiplexer()
    focused_id = mux.get_focused_pane_id()
    # Check if focused pane is a member of this group
    title = mux._run(["display-message", "-t", focused_id, "-p", "#{pane_title}"])
    if title and title.startswith(role_prefix):
        return focused_id
    # Find first pane matching
    panes = _get_panes_by_prefix(role_prefix)
    return panes[0][0] if panes else None


def tab_cycle(role, direction):
    """Cycle through panes with a given role prefix."""
    prefix = f"{role}:" if role and not role.endswith(":") else (role or "term:")
    mux = AdapterResolver.multiplexer()
    panes = _get_panes_by_prefix(prefix)

    if len(panes) <= 1:
        return

    visible = _get_visible_pane(prefix)
    if not visible:
        return

    current_idx = next((i for i, (pid, _) in enumerate(panes) if pid == visible), 0)
    if direction == "next":
        target_idx = (current_idx + 1) % len(panes)
    else:
        target_idx = (current_idx - 1) % len(panes)

    target_id = panes[target_idx][0]
    mux.swap_pane(target_id, visible)
    mux.select_pane(visible)


def tab_new(role, cmd=None):
    """Create a new tab pane for a role."""
    prefix = f"{role}:" if role and not role.endswith(":") else (role or "term:")
    mux = AdapterResolver.multiplexer()
    session = _get_session()

    # Find visible pane for this role
    visible = _get_visible_pane(prefix)
    if not visible:
        # Try to find pane titled exactly the role name
        raw = mux._run(["list-panes", "-s", "-t", session, "-F",
                         "#{pane_id} #{pane_title}"])
        if raw:
            for line in raw.splitlines():
                parts = line.split(" ", 1)
                if len(parts) == 2 and parts[1] == (role or "terminal"):
                    visible = parts[0]
                    break
    if not visible:
        print(f"[INVARIANT] No pane found for role '{role}'", file=sys.stderr)
        return

    # Count existing tabs
    existing = _get_panes_by_prefix(prefix)
    next_num = len(existing) + 1

    # Rename original if needed
    orig_title = mux._run(["display-message", "-t", visible, "-p", "#{pane_title}"])
    if orig_title == (role or "terminal"):
        mux.set_title(visible, f"{prefix}1")
        next_num = 2

    # Split and create new pane
    new_pane = mux.split(visible, direction="v", cwd=os.getcwd())
    if not new_pane:
        return

    mux.set_title(new_pane, f"{prefix}{next_num}")

    if cmd:
        mux.send_command(new_pane, cmd)

    # Swap into visible position
    mux.swap_pane(new_pane, visible)
    mux.select_pane(visible)


def tab_close(role):
    """Close the current tab for a role."""
    prefix = f"{role}:" if role and not role.endswith(":") else (role or "term:")
    mux = AdapterResolver.multiplexer()
    panes = _get_panes_by_prefix(prefix)

    if len(panes) <= 1:
        return

    visible = _get_visible_pane(prefix)
    if not visible:
        return

    # Cycle to next tab first, then kill
    tab_cycle(role, "next")
    mux.kill_pane(visible)


def tab_list(role):
    """List all tabs for a role."""
    prefix = f"{role}:" if role and not role.endswith(":") else (role or "term:")
    mux = AdapterResolver.multiplexer()
    panes = _get_panes_by_prefix(prefix)
    for pid, title in panes:
        cmd = mux._run(["display-message", "-t", pid, "-p", "#{pane_current_command}"])
        print(f"{title} ({cmd or 'shell'}) [{pid}]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: tabs.py <role> <action> [cmd]", file=sys.stderr)
        sys.exit(1)

    role = sys.argv[1] if sys.argv[1] else None
    action = sys.argv[2] if len(sys.argv) > 2 else "next"
    cmd = sys.argv[3] if len(sys.argv) > 3 else None

    if action == "nexus-next":
        nexus_next()
    elif action == "nexus-prev":
        nexus_prev()
    elif action in ("next", "prev"):
        tab_cycle(role, action)
    elif action == "new":
        tab_new(role, cmd)
    elif action == "close":
        tab_close(role)
    elif action == "list":
        tab_list(role)
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)
