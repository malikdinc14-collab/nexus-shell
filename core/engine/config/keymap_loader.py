"""
Keymap configuration loader for nexus-shell.

Reads keymap.conf files and generates tmux bind-key commands.
Supports a cascade of global -> profile -> workspace keymaps,
where workspace overrides profile overrides global.
"""

from __future__ import annotations

import os
import re
from typing import List, Tuple


def _translate_key(raw_key: str) -> str:
    """Translate a human-friendly key name to tmux key notation.

    Examples:
        Alt+F5  -> M-F5
        Alt+p   -> M-p
        Alt+[   -> M-[
    """
    raw_key = raw_key.strip()
    # Handle Alt+ prefix
    match = re.match(r"(?i)Alt\+(.+)", raw_key)
    if match:
        return f"M-{match.group(1)}"
    return raw_key


def parse_keymap(path: str) -> List[Tuple[str, str]]:
    """Read a keymap.conf file and return a list of (key, command) tuples.

    File format (one binding per line):
        Alt+F5 = nexus-ctl workspace save
        Alt+p  = nexus-ctl pack suggest

    Blank lines and lines starting with # are ignored.
    """
    entries: List[Tuple[str, str]] = []
    if not os.path.isfile(path):
        return entries

    with open(path, "r") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key_part, _, cmd_part = stripped.partition("=")
            key = _translate_key(key_part)
            cmd = cmd_part.strip()
            if key and cmd:
                entries.append((key, cmd))
    return entries


def generate_bindings(entries: List[Tuple[str, str]]) -> List[str]:
    """Convert parsed keymap entries into tmux bind-key commands.

    Each entry becomes:
        bind-key -n {key} run-shell "{command}"
    """
    commands: List[str] = []
    for key, cmd in entries:
        commands.append(f'bind-key -n {key} run-shell "{cmd}"')
    return commands


def load_keymap_cascade(
    global_dir: str,
    workspace_dir: str = "",
    profile_dir: str = "",
) -> List[str]:
    """Load keymap.conf from up to 3 directories and merge them.

    Resolution order (later overrides earlier, by key):
        1. global_dir/keymap.conf
        2. profile_dir/keymap.conf  (if profile_dir is non-empty)
        3. workspace_dir/keymap.conf (if workspace_dir is non-empty)

    Returns a merged list of tmux bind-key commands.
    """
    merged: dict[str, str] = {}

    dirs = [global_dir]
    if profile_dir:
        dirs.append(profile_dir)
    if workspace_dir:
        dirs.append(workspace_dir)

    for d in dirs:
        conf_path = os.path.join(d, "keymap.conf")
        entries = parse_keymap(conf_path)
        for key, cmd in entries:
            merged[key] = cmd

    return generate_bindings(list(merged.items()))
