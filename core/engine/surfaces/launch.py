#!/usr/bin/env python3
"""
Launch Nexus Shell with the Textual Surface.

Usage:
    python -m engine.surfaces.launch [session_name] [--cwd /path]

This starts Nexus Shell inside a single terminal window using the
Textual TUI framework. No tmux required.
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure core/ is on the path
CORE_DIR = str(Path(__file__).resolve().parents[2])
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch Nexus Shell with TextualSurface"
    )
    parser.add_argument(
        "session", nargs="?", default="nexus",
        help="Session name (default: nexus)",
    )
    parser.add_argument(
        "--cwd", default="",
        help="Working directory for the workspace",
    )
    parser.add_argument(
        "--pack", default="",
        help="Pack to activate (e.g., python-dev, rust-dev)",
    )
    args = parser.parse_args()

    from engine.surfaces.textual_surface import TextualSurface
    from engine.core import NexusCore

    surface = TextualSurface()
    core = NexusCore(surface, workspace_dir=args.cwd or os.getcwd())

    # Initialize workspace
    session = core.create_workspace(args.session, cwd=args.cwd)

    # Create initial pane with a shell
    surface.create_container(session, command=os.environ.get("SHELL", "/bin/sh"))

    # Start the Textual event loop (blocks)
    surface.run()


if __name__ == "__main__":
    main()
