import subprocess
import json
import sys
from .base import PickerAdapter

class GumAdapter(PickerAdapter):
    def pick(self, context, items_json):
        if not items_json:
            return None
            
        # 1. Extract labels for indexing
        try:
            parsed_items = [json.loads(line) for line in items_json if line.strip()]
        except json.JSONDecodeError:
            return None
            
        labels = [item.get("label", "Unknown") for item in parsed_items]
        labels_str = "\n".join(labels)
        
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(labels_str)
                temp_name = f.name
            
            # 2. Render with Gum Filter (reading from temp file)
            gum_cmd = f"gum filter < {temp_name} --placeholder='Nexus Pulse: {context}...' --indicator='→' --match.foreground='#00FFFF'"
            
            # Launch in a way that preserves TTY
            # We use shell=True and allow stdin to be the terminal
            process = subprocess.run(
                gum_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                text=True
            )
            
            os.unlink(temp_name)
            
            if process.returncode == 0:
                selected_label = process.stdout.strip()
                # Find matching JSON from original list
                for line in items_json:
                    if json.loads(line).get("label") == selected_label:
                        return line
            return None
        except Exception as e:
            print(f"Error in GumAdapter: {e}", file=sys.stderr)
            return None
