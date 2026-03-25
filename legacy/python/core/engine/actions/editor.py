#!/usr/bin/env python3
"""
Editor Actions
==============
Surface-agnostic actions for editor operations.
Composes EditorAdapter + MultiplexerAdapter calls.
"""

import os
import sys
from pathlib import Path
from typing import Optional

_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from engine.actions.resolver import AdapterResolver


def open_file(filepath: str, line: int = 1, column: int = 1,
              focus: bool = True) -> bool:
    """
    Open a file in the editor and optionally focus the editor pane.

    This is the canonical way to open a file from any nexus component
    (yazi, search, menu, AI context). It replaces all direct
    nvim --server + tmux select-pane chains.
    """
    # Resolve canonical path (symlinks, relative paths)
    resolved = str(Path(filepath).resolve())

    editor = AdapterResolver.editor()

    # ── Negative Space: Assert editor is reachable ──
    if not editor.is_available():
        print(f"[INVARIANT] Editor adapter not available. "
              f"Type: {type(editor).__name__}, "
              f"Pipe check failed.", file=sys.stderr)
        return False

    success = editor.open_resource(resolved, line=line, column=column)

    if success and focus:
        _focus_editor_pane()

    return success


def get_current_file() -> Optional[str]:
    """Returns the path of the file currently open in the editor."""
    editor = AdapterResolver.editor()
    if not editor.is_available():
        return None
    return editor.get_current_buffer()


def get_buffer_content(max_lines: int = 200) -> Optional[str]:
    """Returns the text content of the current editor buffer."""
    editor = AdapterResolver.editor()
    if not editor.is_available():
        return None
    return editor.get_buffer_content(max_lines=max_lines)


def get_tabs() -> list:
    """Returns list of open editor tabs."""
    editor = AdapterResolver.editor()
    if not editor.is_available():
        return []
    return editor.get_tabs()


def send_command(cmd: str) -> bool:
    """Sends an arbitrary command to the editor."""
    editor = AdapterResolver.editor()
    if not editor.is_available():
        return False
    return editor.send_editor_command(cmd)


def _focus_editor_pane():
    """Focuses the pane with role 'editor' via the multiplexer."""
    mux = AdapterResolver.multiplexer()
    # Find pane with @nexus_role=editor
    try:
        # Get session ID for listing panes
        session = os.environ.get("NEXUS_SESSION", "")
        if not session:
            # Fall back to getting focused pane's window
            focused = mux.get_focused_pane_id()
            if not focused:
                return
        # List all panes across windows to find editor
        # Use tag lookup via the multiplexer
        windows = mux.list_windows(session) if session else []
        for window in windows:
            for pane in mux.list_panes(window):
                if pane.role == "editor":
                    mux.select_pane(pane.handle)
                    return
    except Exception:
        pass


# ── CLI Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage: editor.py <action> [args...]", file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]

    if action == "open" and len(sys.argv) >= 3:
        filepath = sys.argv[2]
        line = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        col = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        ok = open_file(filepath, line=line, column=col)
        sys.exit(0 if ok else 1)

    elif action == "current-file":
        f = get_current_file()
        if f:
            print(f)
        else:
            sys.exit(1)

    elif action == "buffer":
        max_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        content = get_buffer_content(max_lines=max_lines)
        if content:
            print(content)
        else:
            sys.exit(1)

    elif action == "tabs":
        tabs = get_tabs()
        print(json.dumps(tabs))

    elif action == "command" and len(sys.argv) >= 3:
        cmd = sys.argv[2]
        ok = send_command(cmd)
        sys.exit(0 if ok else 1)

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)
