#!/usr/bin/env python3
# core/engine/capabilities/adapters/null.py
"""
NullAdapter — Headless MultiplexerCapability Test Double
=========================================================
Records all calls made against it. Returns predictable, controlled
responses. Used for:
  - Unit-testing WorkspaceOrchestrator without a real terminal.
  - CI/CD environments with no tmux.
  - Property-based testing compositions.

Usage:
    null = NullAdapter(pane_count=5)
    orch = WorkspaceOrchestrator(nexus_home, project_root,
                                  multiplexer=null)
    orch.apply_composition("vscodelike", "test_session:0")
    assert null.commands_sent["files"] == f"pane_wrapper.sh yazi"
"""

from typing import List, Optional, Dict, Any
from ..base import MultiplexerCapability, PaneInfo, CapabilityType


class NullAdapter(MultiplexerCapability):
    """
    A fully in-memory MultiplexerCapability that never spawns a process.
    All state lives in Python dictionaries.
    """

    def __init__(self, initial_pane_count: int = 1):
        # Simulate the session having one pane already (like a real tmux window)
        self._panes: Dict[str, PaneInfo] = {}
        self._sessions: Dict[str, Dict] = {}
        self._windows: Dict[str, List[str]] = {}  # window -> [pane handles]
        self._env: Dict[str, str] = {}
        self._pane_counter = 0

        # Audit trail
        self.commands_sent: Dict[str, str] = {}   # pane_handle -> last command
        self.keys_sent: Dict[str, list] = {}       # pane_handle -> [keys]
        self.tags: Dict[str, Dict[str, str]] = {}  # pane_handle -> {key: val}
        self.call_log: List[Dict[str, Any]] = []

        # Pre-populate initial panes for the default window
        initial_window = "null_session:0"
        self._windows[initial_window] = []
        for _ in range(initial_pane_count):
            handle = self._new_pane_handle()
            self._panes[handle] = PaneInfo(
                handle=handle, index=len(self._windows[initial_window]),
                width=193, height=64
            )
            self._windows[initial_window].append(handle)

    @property
    def capability_type(self): return CapabilityType.MULTIPLEXER

    def is_available(self) -> bool:
        return True

    def _new_pane_handle(self) -> str:
        h = f"%{self._pane_counter}"
        self._pane_counter += 1
        return h

    def _log(self, method: str, **kwargs):
        self.call_log.append({"method": method, **kwargs})

    # ── Session ──────────────────────────────────────────────────────────────

    def create_session(self, name: str, cwd: str = "",
                       width: int = 220, height: int = 50) -> str:
        self._sessions[name] = {"cwd": cwd, "width": width, "height": height}
        self._windows[f"{name}:0"] = []
        self._log("create_session", name=name)
        return name

    def has_session(self, name: str) -> bool:
        return name in self._sessions

    def attach(self, session: str, client_name: str = "") -> None:
        self._log("attach", session=session)

    def kill_session(self, name: str) -> None:
        self._sessions.pop(name, None)
        self._log("kill_session", name=name)

    # ── Window ───────────────────────────────────────────────────────────────

    def create_window(self, session: str, name: str, cwd: str = "") -> str:
        handle = f"{session}:{name}"
        self._windows[handle] = []
        # Add a seed pane
        ph = self._new_pane_handle()
        self._panes[ph] = PaneInfo(handle=ph, index=0, width=193, height=64)
        self._windows[handle].append(ph)
        self._log("create_window", session=session, name=name)
        return handle

    def list_windows(self, session: str) -> List[str]:
        return [k for k in self._windows if k.startswith(f"{session}:")]

    # ── Pane ─────────────────────────────────────────────────────────────────

    def split(self, target: str, direction: str = "h",
              size: Optional[int] = None, cwd: str = "") -> str:
        # Find which window owns this pane or is this window directly
        window = self._find_window(target)
        if not window:
            return ""
        handle = self._new_pane_handle()
        idx = len(self._windows[window])
        self._panes[handle] = PaneInfo(
            handle=handle, index=idx, width=80, height=24
        )
        self._windows[window].append(handle)
        self._log("split", target=target, direction=direction, new=handle)
        return handle

    def _find_window(self, target: str) -> Optional[str]:
        """Find the window that owns a pane handle, or if target is a window."""
        if target in self._windows:
            return target
        for win, panes in self._windows.items():
            if target in panes:
                return win
        return None

    def kill_pane(self, handle: str) -> None:
        self._panes.pop(handle, None)
        for panes in self._windows.values():
            if handle in panes:
                panes.remove(handle)
        self._log("kill_pane", handle=handle)

    def list_panes(self, window: str) -> List[PaneInfo]:
        handles = self._windows.get(window, [])
        result = []
        for h in handles:
            p = self._panes.get(h)
            if p:
                # Hydrate tags
                p.stack_id = self.tags.get(h, {}).get("@nexus_stack_id", "")
                p.role = self.tags.get(h, {}).get("@nexus_role", "")
                result.append(p)
        return result

    def select_pane(self, handle: str) -> None:
        self._log("select_pane", handle=handle)

    # ── Command Execution ─────────────────────────────────────────────────────

    def send_keys(self, handle: str, keys: str) -> None:
        self.keys_sent.setdefault(handle, []).append(keys)
        self._log("send_keys", handle=handle, keys=keys)

    def send_command(self, handle: str, cmd: str) -> None:
        self.commands_sent[handle] = cmd
        self.keys_sent.setdefault(handle, []).append(cmd)
        self._log("send_command", handle=handle, cmd=cmd)

    # ── Tags ──────────────────────────────────────────────────────────────────

    def set_tag(self, handle: str, key: str, value: str) -> None:
        self.tags.setdefault(handle, {})[key] = value
        self._log("set_tag", handle=handle, key=key, value=value)

    def get_tag(self, handle: str, key: str) -> str:
        return self.tags.get(handle, {}).get(key, "")

    # ── Layout ────────────────────────────────────────────────────────────────

    def apply_layout(self, window: str, layout: str) -> bool:
        self._log("apply_layout", window=window, layout=layout)
        return True  # Always succeeds in null mode

    def get_dimensions(self, target: str) -> Dict[str, int]:
        return {"width": 193, "height": 64}

    # ── Environment ───────────────────────────────────────────────────────────

    def set_env(self, session: str, key: str, value: str) -> None:
        self._env[key] = value
        self._log("set_env", session=session, key=key)

    # ── Test Helpers ──────────────────────────────────────────────────────────

    def assert_pane_has_command(self, stack_id: str, expected_substr: str):
        """Helper for tests: assert a pane with given stack_id ran a command."""
        for handle, tags in self.tags.items():
            if tags.get("@nexus_stack_id") == stack_id:
                cmd = self.commands_sent.get(handle, "")
                assert expected_substr in cmd, (
                    f"Pane '{stack_id}' expected '{expected_substr}' "
                    f"in command, got: '{cmd}'"
                )
                return
        raise AssertionError(f"No pane found with stack_id='{stack_id}'")

    def dump(self) -> str:
        """Return a human-readable state dump for debugging."""
        lines = ["[NullAdapter State]"]
        for win, handles in self._windows.items():
            lines.append(f"  Window: {win}")
            for h in handles:
                p = self._panes.get(h)
                t = self.tags.get(h, {})
                cmd = self.commands_sent.get(h, "<none>")
                lines.append(
                    f"    {h:6} [{t.get('@nexus_stack_id', 'UNIDENTIFIED'):15}] "
                    f"CMD: {cmd[:50]}"
                )
        return "\n".join(lines)
