#!/usr/bin/env python3
"""
Action Dispatcher
=================
Single CLI entry point for all nexus actions.
Shell scripts call this instead of making direct tmux/nvim calls.

Usage:
  python3 dispatch.py editor.open /path/to/file [line] [col]
  python3 dispatch.py editor.current-file
  python3 dispatch.py editor.buffer [max_lines]
  python3 dispatch.py editor.tabs
  python3 dispatch.py editor.command ":tabedit foo<CR>"
  python3 dispatch.py pane.focus editor          # by role
  python3 dispatch.py pane.focus %5              # by handle
  python3 dispatch.py pane.split h
  python3 dispatch.py pane.kill [handle]
  python3 dispatch.py pane.capture [handle] [lines]
  python3 dispatch.py pane.id
  python3 dispatch.py pane.send-keys %5 "ls<CR>"

INVARIANT: This module delegates to action modules which delegate to
adapters. No surface-specific calls exist here.
"""

import sys
import os
import json
from pathlib import Path

# Ensure engine is importable
_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))


def main():
    if len(sys.argv) < 2:
        print("Usage: dispatch.py <domain.action> [args...]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    # Parse domain.action
    if "." not in command:
        print(f"[INVARIANT] Command must be domain.action format, got: {command}",
              file=sys.stderr)
        sys.exit(1)

    domain, action = command.split(".", 1)

    if domain == "editor":
        from engine.actions import editor as ed

        if action == "open" and args:
            filepath = args[0]
            line = int(args[1]) if len(args) > 1 else 1
            col = int(args[2]) if len(args) > 2 else 1
            ok = ed.open_file(filepath, line=line, column=col)
            sys.exit(0 if ok else 1)

        elif action == "current-file":
            f = ed.get_current_file()
            if f:
                print(f)
            else:
                sys.exit(1)

        elif action == "buffer":
            max_lines = int(args[0]) if args else 200
            content = ed.get_buffer_content(max_lines=max_lines)
            if content:
                print(content)
            else:
                sys.exit(1)

        elif action == "tabs":
            print(json.dumps(ed.get_tabs()))

        elif action == "command" and args:
            ok = ed.send_command(args[0])
            sys.exit(0 if ok else 1)

        else:
            print(f"Unknown editor action: {action}", file=sys.stderr)
            sys.exit(1)

    elif domain == "pane":
        from engine.actions import pane as pn

        if action == "focus" and args:
            target = args[0]
            if not target.startswith("%"):
                ok = pn.focus_by_role(target)
            else:
                pn.focus(target)
                ok = True
            sys.exit(0 if ok else 1)

        elif action == "split":
            direction = args[0] if args else "h"
            new = pn.split(direction=direction)
            if new:
                print(new)
            else:
                sys.exit(1)

        elif action == "kill":
            handle = args[0] if args else ""
            pn.kill(handle)

        elif action == "respawn" and len(args) >= 2:
            pn.respawn(args[0], args[1])

        elif action == "swap" and len(args) >= 2:
            pn.swap(args[0], args[1])

        elif action == "resize":
            handle = args[0] if args else ""
            height = int(args[1]) if len(args) > 1 else None
            pn.resize(handle, height=height)

        elif action == "capture":
            handle = args[0] if args else ""
            lines = int(args[1]) if len(args) > 1 else 50
            print(pn.capture_output(handle, lines))

        elif action == "id":
            print(pn.get_focused_id())

        elif action == "send-keys" and len(args) >= 2:
            pn.send_keys(args[0], args[1])

        elif action == "send-command" and len(args) >= 2:
            pn.send_command(args[0], args[1])

        elif action == "zoom":
            handle = args[0] if args else ""
            pn.zoom(handle)

        elif action == "display-message" and args:
            pn.display_message(args[0])

        elif action == "select-window" and args:
            pn.select_window(args[0])

        elif action == "metadata" and len(args) >= 2:
            handle, key = args[0], args[1]
            if len(args) > 2:
                pn.set_metadata(handle, key, args[2])
            else:
                print(pn.get_metadata(handle, key))

        else:
            print(f"Unknown pane action: {action}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Unknown domain: {domain}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
