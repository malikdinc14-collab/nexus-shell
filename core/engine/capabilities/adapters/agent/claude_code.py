#!/usr/bin/env python3
"""
Claude Code Capability Adapter
===============================
Maps ChatCapability interface to the Claude Code CLI.
"""

import subprocess
from typing import Optional, List, Dict
from ...base import ChatCapability, AdapterManifest, CapabilityType


class ClaudeCodeAdapter(ChatCapability):
    """Adapter for the Claude Code CLI agent."""

    manifest = AdapterManifest(
        name="claude-code",
        capability_type=CapabilityType.CHAT,
        binary="claude",
        priority=110,
    )

    STARTUP_DELAY_SECS: float = 1.0
    MIN_WIDTH: int = 60
    MIN_HEIGHT: int = 15

    def __init__(self):
        self._bin = self._resolve_binary()

    def _resolve_binary(self) -> Optional[str]:
        try:
            path = subprocess.check_output(
                ["which", "claude"], stderr=subprocess.DEVNULL
            ).decode().strip()
            return path if path else None
        except Exception:
            return None

    @property
    def capability_type(self):
        return CapabilityType.CHAT

    def is_available(self) -> bool:
        return self._bin is not None

    def get_launch_command(self) -> str:
        if not self._bin:
            return "echo '[ERROR] claude not found'"
        return f"sleep {self.STARTUP_DELAY_SECS} && {self._bin}"

    def get_launch_constraints(self) -> Dict:
        return {
            "min_width": self.MIN_WIDTH,
            "min_height": self.MIN_HEIGHT,
            "requires_attached_tty": True,
            "startup_delay": self.STARTUP_DELAY_SECS,
        }

    def send_message(self, message: str) -> str:
        return ""

    def get_history(self) -> List[Dict[str, str]]:
        return []
