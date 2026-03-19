import subprocess
import json
import sys
import shutil
from typing import List, Optional
from ...base import MenuCapability

class FzfMenuAdapter(MenuCapability):
    """Implementation of MenuCapability using the 'fzf' command-line fuzzy finder."""

    @property
    def capability_type(self):
        from ...base import CapabilityType
        return CapabilityType.MENU

    @property
    def capability_id(self): return "fzf"

    def is_available(self) -> bool:
        return shutil.which("fzf") is not None

    def show_menu(self, options: List[str], prompt: str = "Select:") -> Optional[str]:
        if not options:
            return None
            
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write("\n".join(options))
                temp_name = f.name
                
            fzf_cmd = f"fzf --prompt='{prompt} ' < {temp_name}"
            
            with open("/dev/tty", "r") as tty:
                process = subprocess.run(
                    fzf_cmd,
                    shell=True,
                    stdin=tty,
                    stdout=subprocess.PIPE,
                    text=True
                )
            
            os.unlink(temp_name)
            
            if process.returncode == 0:
                answer = process.stdout.strip()
                return answer if answer else None
            return None
        except Exception:
            return None

    def pick(self, context: str, items_json: List[str]) -> Optional[str]:
        if not items_json:
            return None
            
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write("\n".join(items_json))
                temp_name = f.name
                
            # Formatting for the engine JSON/TSV hybrid
            fzf_cmd = f"fzf --ansi --header='Nexus Pulse: {context}' --reverse --height=100% --border=none --info=inline --prompt='> ' --with-nth=1 --delimiter='\\t' < {temp_name}"
            
            with open("/dev/tty", "r") as tty:
                process = subprocess.run(
                    fzf_cmd,
                    shell=True,
                    stdin=tty,
                    stdout=subprocess.PIPE,
                    text=True
                )
            
            os.unlink(temp_name)
            
            if process.returncode == 0:
                selected_line = process.stdout.strip()
                return selected_line
            return None
        except Exception as e:
            print(f"Error in FzfMenuAdapter: {e}", file=sys.stderr)
            return None
