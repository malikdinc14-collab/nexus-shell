import os
import subprocess
from typing import List, Dict, Any, Optional
from ..base import ExplorerCapability

class YaziAdapter(ExplorerCapability):
    """Implementation of ExplorerCapability using the Yazi TUI."""
    
    def __init__(self, nexus_home: str):
        self.nexus_home = nexus_home
        self.config_dir = os.path.join(nexus_home, "config", "yazi")

    def is_available(self) -> bool:
        return subprocess.run(["which", "yazi"], capture_output=True).returncode == 0

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
        except:
            pass
        return items

    def get_selection(self) -> Optional[str]:
        # Implementation depends on reading a temp file that Yazi writes to on selection.
        # This will be refined as we deepen the RPC integration.
        return None

    def trigger_action(self, action: str, payload: Any) -> bool:
        # e.g., 'open', 'copy'
        return False
