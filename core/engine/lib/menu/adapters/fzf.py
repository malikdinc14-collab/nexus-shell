import subprocess
import json
from .base import PickerAdapter

class FzfAdapter(PickerAdapter):
    def pick(self, context, items_json):
        if not items_json:
            return None
            
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write("\n".join(items_json))
                temp_name = f.name
                
            fzf_cmd = f"fzf --ansi --header='Nexus Pulse: {context}' --reverse --height=100% --border=none --info=inline --prompt='> ' --with-nth=1 --delimiter='\\t' < {temp_name}"
            
            process = subprocess.run(
                fzf_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                text=True
            )
            
            os.unlink(temp_name)
            
            if process.returncode == 0:
                selected_line = process.stdout.strip()
                return selected_line
            return None
        except Exception as e:
            print(f"Error in FzfAdapter: {e}", file=sys.stderr)
            return None
