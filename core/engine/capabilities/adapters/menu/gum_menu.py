import os
import subprocess
import shutil
from typing import List, Optional
from ...base import MenuCapability

class GumMenuAdapter(MenuCapability):
    """Implementation of MenuCapability using the bash 'gum' tool."""

    @property
    def capability_type(self):
        from ...base import CapabilityType
        return CapabilityType.MENU

    @property
    def capability_id(self): return "gum"

    def is_available(self) -> bool:
        return shutil.which("gum") is not None

    def show_menu(self, options: List[str], prompt: str = "Select:") -> Optional[str]:
        if not options:
            return None
            
        try:
            # Gum requires a TTY to render interactively. 
            # We open /dev/tty so it can take over the terminal even if called via a script
            with open("/dev/tty", "r") as tty:
                result = subprocess.run(
                    ["gum", "choose", "--header", prompt] + options,
                    stdin=tty,
                    capture_output=True,
                    text=True
                )
            if result.returncode == 0:
                answer = result.stdout.strip()
                return answer if answer else None
            return None
        except Exception:
            return None
