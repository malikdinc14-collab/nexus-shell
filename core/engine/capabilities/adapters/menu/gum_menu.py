import os
import subprocess
import shutil
from typing import List, Optional
from ...base import MenuCapability, AdapterManifest, CapabilityType

class GumMenuAdapter(MenuCapability):
    """Implementation of MenuCapability using the bash 'gum' tool."""

    manifest = AdapterManifest(
        name="gum",
        capability_type=CapabilityType.MENU,
        binary="gum",
        priority=80,
    )

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

    def pick(self, context: str, items_json: List[str]) -> Optional[str]:
        if not items_json:
            return None
            
        import tempfile
        import json
        import sys
        
        try:
            parsed_items = [json.loads(line) for line in items_json if line.strip()]
        except json.JSONDecodeError:
            return None
            
        labels = [item.get("label", "Unknown") for item in parsed_items]
        labels_str = "\n".join(labels)
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(labels_str)
                temp_name = f.name
            
            gum_cmd = f"gum filter < {temp_name} --placeholder='Nexus Pulse: {context}...' --indicator='→' --match.foreground='#00FFFF'"
            
            with open("/dev/tty", "r") as tty:
                process = subprocess.run(
                    gum_cmd,
                    shell=True,
                    stdin=tty,
                    stdout=subprocess.PIPE,
                    text=True
                )
            
            os.unlink(temp_name)
            
            if process.returncode == 0:
                selected_label = process.stdout.strip()
                for line in items_json:
                    if json.loads(line).get("label") == selected_label:
                        return line
            return None
        except Exception as e:
            print(f"Error in GumMenuAdapter: {e}", file=sys.stderr)
            return None

