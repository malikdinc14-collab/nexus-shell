#!/usr/bin/env python3
"""
Pane Actions
============
Surface-agnostic actions for pane management.
Wraps MultiplexerAdapter calls with intent-level semantics.
"""

import os
import sys
from pathlib import Path
from typing import Optional

_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from engine.actions.resolver import AdapterResolver


def get_focused_id() -> str:
    """Returns the handle of the currently focused pane."""
    return AdapterResolver.multiplexer().get_focused_pane_id()


def focus_by_role(role: str) -> bool:
    """Focuses the pane with the given @nexus_role."""
    mux = AdapterResolver.multiplexer()
    session = os.environ.get("NEXUS_SESSION", "")
    if not session:
        return False
    try:
        for window in mux.list_windows(session):
            for pane in mux.list_panes(window):
                if pane.role == role:
                    mux.select_pane(pane.handle)
                    return True
    except Exception:
        pass
    return False


def focus(handle: str) -> None:
    """Focuses a pane by its handle."""
    AdapterResolver.multiplexer().select_pane(handle)


def split(direction: str = "h", cmd: str = "", cwd: str = "") -> Optional[str]:
    """Splits the focused pane. Returns new pane handle."""
    mux = AdapterResolver.multiplexer()
    target = mux.get_focused_pane_id()
    if not target:
        return None
    new_handle = mux.split(target, direction=direction, cwd=cwd or os.getcwd())
    if new_handle and cmd:
        mux.send_command(new_handle, cmd)
    return new_handle


def kill(handle: str = "") -> None:
    """Kills a pane by handle, or the focused pane if no handle given."""
    mux = AdapterResolver.multiplexer()
    target = handle or mux.get_focused_pane_id()
    if target:
        mux.kill_pane(target)


def swap(source: str, target: str) -> None:
    """Swaps the contents of two panes."""
    AdapterResolver.multiplexer().swap_pane(source, target)


def resize(handle: str = "", height: Optional[int] = None,
           width: Optional[int] = None) -> None:
    """Resizes a pane."""
    mux = AdapterResolver.multiplexer()
    target = handle or mux.get_focused_pane_id()
    if target:
        mux.resize_pane(target, height=height, width=width)


def respawn(handle: str, cmd: str) -> None:
    """Kills the current process in a pane and starts a new one."""
    AdapterResolver.multiplexer().respawn_pane(handle, cmd)


def capture_output(handle: str = "", lines: int = 50) -> str:
    """Captures visible output from a pane."""
    mux = AdapterResolver.multiplexer()
    target = handle or mux.get_focused_pane_id()
    if not target:
        return ""
    return mux.capture_output(target, lines=lines)


def send_keys(handle: str, keys: str) -> None:
    """Sends keystrokes to a pane."""
    AdapterResolver.multiplexer().send_keys(handle, keys)


def send_command(handle: str, cmd: str) -> None:
    """Sends a command + ENTER to a pane."""
    AdapterResolver.multiplexer().send_command(handle, cmd)


def get_metadata(handle: str, key: str) -> str:
    """Gets a metadata tag from a pane."""
    return AdapterResolver.multiplexer().get_tag(handle, key)


def set_metadata(handle: str, key: str, value: str) -> None:
    """Sets a metadata tag on a pane."""
    AdapterResolver.multiplexer().set_tag(handle, key, value)


def zoom(handle: str = "") -> None:
    """Toggles zoom state of a pane."""
    mux = AdapterResolver.multiplexer()
    target = handle or mux.get_focused_pane_id()
    if target and hasattr(mux, '_run'):
        mux._run(["resize-pane", "-Z", "-t", target])


def display_message(msg: str) -> None:
    """Shows a transient message in the multiplexer status line."""
    mux = AdapterResolver.multiplexer()
    if hasattr(mux, '_run'):
        mux._run(["display-message", msg])


def select_window(target: str) -> None:
    """Selects a window by index or name."""
    mux = AdapterResolver.multiplexer()
    if hasattr(mux, '_run'):
        mux._run(["select-window", "-t", target])


def list_all(session: str = "") -> list:
    """Lists all panes in the session."""
    mux = AdapterResolver.multiplexer()
    session = session or os.environ.get("NEXUS_SESSION", "")
    if not session:
        return []
    result = []
    for window in mux.list_windows(session):
        result.extend(mux.list_panes(window))
    return result


# ── CLI Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pane.py <action> [args...]", file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]

    if action == "focus" and len(sys.argv) >= 3:
        target = sys.argv[2]
        # If target looks like a role name (not %N), focus by role
        if not target.startswith("%"):
            ok = focus_by_role(target)
        else:
            focus(target)
            ok = True
        sys.exit(0 if ok else 1)

    elif action == "split":
        direction = sys.argv[2] if len(sys.argv) > 2 else "h"
        new = split(direction=direction)
        if new:
            print(new)
        else:
            sys.exit(1)

    elif action == "kill":
        handle = sys.argv[2] if len(sys.argv) > 2 else ""
        kill(handle)

    elif action == "capture":
        handle = sys.argv[2] if len(sys.argv) > 2 else ""
        lines = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        print(capture_output(handle, lines))

    elif action == "id":
        print(get_focused_id())

    elif action == "zoom":
        handle = sys.argv[2] if len(sys.argv) > 2 else ""
        zoom(handle)

    elif action == "display-message" and len(sys.argv) >= 3:
        display_message(sys.argv[2])

    elif action == "select-window" and len(sys.argv) >= 3:
        select_window(sys.argv[2])

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)
