# modules/menu/lib/providers/session_provider.py
import subprocess
from lib.core.menu_engine import fmt

def provide(subfolder=""):
    """Lists active tmux sessions with telemetry (window count, active time)."""
    try:
        # Get sessions: NAME: WINDOWS [DATE]
        result = subprocess.check_output([
            "tmux", "list-sessions", "-F", "#{session_name}\t#{session_windows}\t#{session_created}"
        ]).decode().strip()
        
        if not result:
            return [fmt("No active sessions", "DISABLED", "NONE")]
            
        items = []
        for line in result.split("\n"):
            parts = line.split("\t")
            if len(parts) >= 3:
                name, windows, created = parts[0], parts[1], parts[2]
                items.append(fmt(f"📁 {name}", "ACTION", f"tmux switch-client -t '{name}'", 
                                 description=f"Windows: {windows} | Created: {created}",
                                 color="blue"))
        return items
    except Exception as e:
        return [fmt(f"Session Error: {e}", "ERROR", "NONE")]
