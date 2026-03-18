#!/usr/bin/env python3
# core/engine/capabilities/adapters/tmux.py
"""
Tmux MultiplexerAdapter
========================
Concrete implementation of MultiplexerCapability backed by tmux.

This adapter wraps all tmux subprocess calls so the WorkspaceOrchestrator
never touches tmux directly. To add Ghostty, WezTerm, or iTerm2 support,
write a new adapter implementing MultiplexerCapability — nothing else changes.

Invariants enforced by this adapter:
  - All tmux commands use -L <socket_label> for session isolation.
  - list_panes() always returns PaneInfo objects (never raw strings).
  - split() always returns the new pane handle via -P -F #{pane_id}.
  - set_tag / get_tag use tmux pane options (@nexus_*).
"""

import os
import subprocess
from typing import List, Optional, Dict
from ...base import MultiplexerCapability, PaneInfo, CapabilityType


class TmuxAdapter(MultiplexerCapability):
    """
    Drives tmux through subprocess. All commands go through _run().
    socket_label isolates this session from other tmux servers.
    """

    def __init__(self, socket_label: str = "", conf: str = ""):
        self.socket_label = socket_label
        self.conf = conf

    @property
    def capability_type(self): return CapabilityType.MULTIPLEXER

    def is_available(self) -> bool:
        try:
            subprocess.check_output(["tmux", "-V"], stderr=subprocess.DEVNULL)
            return True
        except FileNotFoundError:
            return False

    # ── Internal ─────────────────────────────────────────────────────────────

    def _run(self, args: List[str]) -> str:
        """Run a tmux command and return stripped stdout. Empty string on error."""
        cmd = ["tmux"]
        if self.socket_label:
            cmd += ["-L", self.socket_label]
        if self.conf:
            cmd += ["-f", self.conf]
        cmd += args
        try:
            result = subprocess.check_output(
                cmd, stderr=subprocess.PIPE, timeout=10
            )
            return result.decode("utf-8", errors="replace").strip()
        except subprocess.CalledProcessError:
            return ""
        except Exception:
            return ""

    # ── Session Management ────────────────────────────────────────────────────

    def create_session(self, name: str, cwd: str = "",
                       width: int = 220, height: int = 50) -> str:
        args = ["new-session", "-d", "-s", name,
                "-x", str(width), "-y", str(height)]
        if cwd:
            args += ["-c", cwd]
        self._run(args)
        return name

    def has_session(self, name: str) -> bool:
        result = self._run(["has-session", "-t", name])
        return result is not None  # _run returns "" (not None) on error

    def attach(self, session: str, client_name: str = "") -> None:
        args = ["new-session", "-d", "-t", session]
        if client_name:
            args += ["-s", client_name]
        self._run(args)

    def kill_session(self, name: str) -> None:
        self._run(["kill-session", "-t", name])

    # ── Window Management ─────────────────────────────────────────────────────

    def create_window(self, session: str, name: str, cwd: str = "") -> str:
        args = ["new-window", "-d", "-t", session, "-n", name]
        if cwd:
            args += ["-c", cwd]
        self._run(args)
        return f"{session}:{name}"

    def list_windows(self, session: str) -> List[str]:
        raw = self._run(["list-windows", "-t", session, "-F", "#{window_index}"])
        return [f"{session}:{idx}" for idx in raw.splitlines() if idx]

    # ── Pane Management ───────────────────────────────────────────────────────

    def split(self, target: str, direction: str = "h",
              size: Optional[int] = None, cwd: str = "") -> str:
        flag = "-h" if direction == "h" else "-v"
        args = ["split-window", flag, "-d", "-t", target,
                "-P", "-F", "#{pane_id}"]
        if size:
            args += ["-p", str(size)]
        if cwd:
            args += ["-c", cwd]
        return self._run(args)

    def kill_pane(self, handle: str) -> None:
        self._run(["kill-pane", "-t", handle])

    def list_panes(self, window: str) -> List[PaneInfo]:
        fmt = (
            "#{pane_index}|#{pane_id}|#{pane_width}|#{pane_height}"
            "|#{pane_left}|#{pane_top}"
            "|#{@nexus_stack_id}|#{@nexus_role}|#{pane_current_command}"
        )
        raw = self._run(["list-panes", "-t", window, "-F", fmt])
        panes = []
        for line in raw.splitlines():
            parts = line.split("|")
            if len(parts) < 9:
                continue
            idx, handle, w, h, x, y, sid, role, cmd = parts
            panes.append(PaneInfo(
                handle=handle,
                index=int(idx),
                width=int(w), height=int(h),
                x=int(x), y=int(y),
                stack_id=sid, role=role, command=cmd,
            ))
        return panes

    def select_pane(self, handle: str) -> None:
        self._run(["select-pane", "-t", handle])

    # ── Command Execution ─────────────────────────────────────────────────────

    def send_keys(self, handle: str, keys: str) -> None:
        self._run(["send-keys", "-t", handle, keys])

    def send_command(self, handle: str, cmd: str) -> None:
        self._run(["send-keys", "-t", handle, cmd, "ENTER"])

    # ── Tag / Metadata ────────────────────────────────────────────────────────

    def set_tag(self, handle: str, key: str, value: str) -> None:
        self._run(["set-option", "-p", "-t", handle, key, value])

    def get_tag(self, handle: str, key: str) -> str:
        v = self._run(["display-message", "-t", handle, "-p", f"#{{@{key}}}"])
        return v.strip() if v else ""

    def set_title(self, handle: str, title: str) -> None:
        self._run(["select-pane", "-t", handle, "-T", title])

    # ── Layout ────────────────────────────────────────────────────────────────

    def apply_layout(self, window: str, layout: str) -> bool:
        result = self._run(["select-layout", "-t", window, layout])
        return result is not None

    def get_dimensions(self, target: str) -> Dict[str, int]:
        raw = self._run(["display-message", "-t", target, "-p",
                         "#{window_width},#{window_height}"])
        try:
            w, h = raw.split(",")
            return {"width": int(w), "height": int(h)}
        except Exception:
            return {"width": 80, "height": 24}

    # ── Environment ───────────────────────────────────────────────────────────

    def set_env(self, session: str, key: str, value: str) -> None:
        self._run(["set-environment", "-t", session, key, value])
        self._run(["set-environment", "-g", key, value])
