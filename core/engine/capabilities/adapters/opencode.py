#!/usr/bin/env python3
# core/engine/capabilities/adapters/opencode.py
"""
OpenCode Capability Adapter
===========================
Maps ChatCapability interface to OpenCode TUI.

OpenCode is a Node-based TUI chat agent. It has two key boot invariants:
  1. It must be launched in an attached, interactive TTY.
  2. It requires a minimum pane size (approx. 40x12).

The adapter exposes these constraints so the orchestrator can make
correct decisions without hardcoding tool names in kernel scripts.
"""

import subprocess
from pathlib import Path
from typing import Optional, List, Dict
from ..base import ChatCapability


class OpenCodeAdapter(ChatCapability):
    """
    Adapter for the OpenCode AI agent TUI.
    """

    # Invariant: OpenCode requires an attached TTY before launch.
    # Declare the minimum startup delay (seconds) needed after pane creation.
    STARTUP_DELAY_SECS: float = 1.5

    # Invariant: Minimum geometry for readable TUI.
    MIN_WIDTH: int = 40
    MIN_HEIGHT: int = 12

    def __init__(self):
        self._bin = self._resolve_binary()

    def _resolve_binary(self) -> Optional[str]:
        """Resolve the full path of the opencode binary."""
        try:
            path = subprocess.check_output(
                ["which", "opencode"], stderr=subprocess.DEVNULL
            ).decode().strip()
            return path if path else None
        except Exception:
            return None

    @property
    def capability_type(self):
        from ..base import CapabilityType
        return CapabilityType.CHAT

    def is_available(self) -> bool:
        return self._bin is not None

    def get_launch_command(self) -> str:
        """
        Returns the shell command to launch opencode, including any
        required startup delay. This is the single source of truth for
        how to boot this tool.
        """
        if not self._bin:
            return "echo '[ERROR] opencode not found'"
        # Use sleep to let the pane attach before TUI init
        return f"sleep {self.STARTUP_DELAY_SECS} && {self._bin}"

    def get_launch_constraints(self) -> Dict:
        """Returns geometry constraints for the orchestrator."""
        return {
            "min_width": self.MIN_WIDTH,
            "min_height": self.MIN_HEIGHT,
            "requires_attached_tty": True,
            "startup_delay": self.STARTUP_DELAY_SECS,
        }

    # --- ChatCapability interface ---
    def send_message(self, message: str) -> str:
        # OpenCode is a TUI — not RPC-driven yet.
        return ""

    def get_history(self) -> List[Dict[str, str]]:
        return []
