import os
import subprocess
from typing import List, Dict, Any, Optional
from ...base import ExplorerCapability, AdapterManifest, CapabilityType


class YaziAdapter(ExplorerCapability):
    """Implementation of ExplorerCapability using the Yazi TUI."""

    # Yazi is a TUI — it needs an attached terminal before launch.
    STARTUP_DELAY_SECS: float = 0.5

    manifest = AdapterManifest(
        name="yazi",
        capability_type=CapabilityType.EXPLORER,
        binary="yazi",
        priority=100,
    )

    def __init__(self, nexus_home: str = ""):
        self.nexus_home = nexus_home
        self.config_dir = os.path.join(nexus_home, "config", "yazi") if nexus_home else ""
        self._bin = self._resolve_binary()

    def _resolve_binary(self) -> Optional[str]:
        try:
            return subprocess.check_output(
                ["which", "yazi"], stderr=subprocess.DEVNULL
            ).decode().strip() or None
        except Exception:
            return None

    def get_launch_command(self) -> str:
        """Adapter-declared launch command for the orchestrator."""
        bin_path = self._bin or "yazi"
        return f"sleep {self.STARTUP_DELAY_SECS} && {bin_path}"

    def is_available(self) -> bool:
        return self._bin is not None

    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        # Yazi doesn't provide a direct JSON list API easily without running the TUI.
        # For now, we fall back to standard os.listdir to populate the capability.
        items = []
        try:
            for entry in os.scandir(path):
                items.append({
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if not entry.is_dir() else None
                })
        except Exception:
            pass
        return items

    def get_selection(self) -> Optional[str]:
        # Implementation depends on reading a temp file that Yazi writes to on selection.
        # This will be refined as we deepen the RPC integration.
        return None

    def trigger_action(self, action: str, payload: Any) -> bool:
        # e.g., 'open', 'copy'
        return False
