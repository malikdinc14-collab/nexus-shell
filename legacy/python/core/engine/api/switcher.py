#!/usr/bin/env python3
# core/engine/api/switcher.py
"""
Nexus Master Switcher (nxs-switch)
====================================
Port of core/kernel/exec/switcher.sh

Context-aware fuzzy switcher. Invoked via Alt-m keybind.

Behavior:
  - In editor pane with nvim RPC: switch nvim tabs or buffers
  - In terminal pane: switch shell tabs (via terminal_tabs.sh)
  - Anywhere else: switch tmux windows (global project slots)
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional

# Make engine importable
_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

# [INVARIANT] All multiplexer operations route through AdapterResolver
from engine.actions.resolver import AdapterResolver

# Legacy path setup for control_bridge (migrated separately)
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from control_bridge import ControlBridge

MUX = AdapterResolver.multiplexer()


def tmux_query(fmt: str) -> str:
    """Query a single tmux format string from the current pane context."""
    return MUX._run(["display-message", "-p", fmt]) or ""


def fzf_pick(lines: list[str], header: str) -> Optional[str]:
    """Show an fzf popup and return the selected line, or None if cancelled."""
    if not lines:
        return None
    text = "\n".join(lines)
    try:
        result = subprocess.run(
            ["fzf-tmux", "-p", "60%,40%", "--header", header, "--reverse"],
            input=text,
            capture_output=True,
            text=True,
        )
        choice = result.stdout.strip()
        return choice if choice else None
    except FileNotFoundError:
        # fzf-tmux not available — fall back to plain fzf
        try:
            result = subprocess.run(
                ["fzf", "--header", header, "--reverse"],
                input=text,
                capture_output=True,
                text=True,
            )
            choice = result.stdout.strip()
            return choice if choice else None
        except FileNotFoundError:
            return None


def nvim_remote_expr(pipe: Path, expr: str) -> str:
    """Evaluate a VimL expression via the editor adapter."""
    editor = AdapterResolver.editor()
    return editor.remote_expr(expr)


def switch_nvim(bridge: ControlBridge, pipe: Path) -> None:
    """Switch nvim tab or buffer via RPC."""
    # Try tabs first
    tab_json = nvim_remote_expr(
        pipe,
        "JSON.stringify(map(gettabinfo(), {k, v -> v.tabnr . ': ' . fnamemodify(bufname(v.windows[0]), ':t')}))",
    )
    try:
        tabs = json.loads(tab_json) if tab_json else []
    except json.JSONDecodeError:
        tabs = []

    if not tabs:
        # Fall back to listed buffers
        buf_json = nvim_remote_expr(
            pipe,
            "JSON.stringify(map(filter(getbufinfo({'buflisted':1}), {k, v -> v.name != ''}), "
            "{k, v -> v.bufnr . ': ' . fnamemodify(v.name, ':t')}))",
        )
        try:
            tabs = json.loads(buf_json) if buf_json else []
        except json.JSONDecodeError:
            tabs = []

    if not tabs:
        return

    choice = fzf_pick(tabs, "Nvim: Switch Tab/Buffer")
    if not choice:
        return

    item_id = choice.split(":")[0].strip()
    if "Tab" in choice:
        bridge.send_to_editor(f"<C-\\><C-n>:{item_id}tabnext<CR>")
    else:
        bridge.send_to_editor(f"<C-\\><C-n>:buffer {item_id}<CR>")


def switch_terminal(pane_id: str, nexus_home: str) -> None:
    """Switch between shell tabs in a terminal pane."""
    terminal_tabs = Path(nexus_home) / "core/terminal_tabs.sh"
    tabs = []

    if terminal_tabs.exists():
        try:
            out = subprocess.check_output(
                [str(terminal_tabs), "list"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            tabs = [l for l in out.splitlines() if l]
        except subprocess.CalledProcessError:
            pass

    if not tabs:
        return

    choice = fzf_pick(tabs, "Shell: Switch Tab")
    if not choice:
        return

    # Extract pane handle from "[%23]" style notation
    import re
    match = re.search(r'\[(%\d+)\]', choice)
    if match:
        target_pane = match.group(1)
        MUX.swap_pane(target_pane, pane_id)
        MUX.select_pane(pane_id)


def switch_global(session_id: str) -> None:
    """Switch between tmux windows (global project slots)."""
    out = MUX._run(["list-windows", "-t", session_id, "-F", "#I: #{window_name}"])
    if not out:
        return

    slots = [l for l in out.splitlines() if l]
    if not slots:
        return

    choice = fzf_pick(slots, "Global: Switch Project Slot")
    if not choice:
        return

    idx = choice.split(":")[0].strip()
    MUX._run(["select-window", "-t", f":{idx}"])


def main() -> int:
    nexus_home = os.environ.get("NEXUS_HOME", str(Path(__file__).resolve().parents[3]))

    bridge   = ControlBridge()
    pane_id  = tmux_query("#{pane_id}")
    title    = tmux_query("#{pane_title}")
    session  = tmux_query("#S")

    # Context 1: editor pane with live nvim RPC
    if title == "editor":
        pipe = bridge.get_nvim_pipe()
        if pipe:
            switch_nvim(bridge, pipe)
            return 0

    # Context 2: terminal/shell pane
    if title.startswith("term:") or title == "terminal":
        switch_terminal(pane_id, nexus_home)
        return 0

    # Context 3: global — switch tmux windows
    switch_global(session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
