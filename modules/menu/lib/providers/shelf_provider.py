# modules/menu/lib/providers/shelf_provider.py
import os
import subprocess
from lib.core.menu_engine import fmt

def provide(subfolder=""):
    """Lists panes currently stowed on the Shelf."""
    # We can still call the shelf script but wrap it in our fmt
    # or just do the tmux calls here for better control.
    
    session_id = os.environ.get("SESSION_ID")
    if not session_id:
        try:
            session_id = subprocess.check_output(["tmux", "display-message", "-p", "#S"]).decode().strip()
        except:
            return [fmt("Tmux session not found", "ERROR", "NONE")]
            
    reservoir = "NEXUS_SHELF"
    
    try:
        # Check if window exists
        subprocess.run(["tmux", "has-session", "-t", f"{session_id}:{reservoir}"], check=True, capture_output=True)
        
        result = subprocess.check_output([
            "tmux", "list-panes", "-t", f"{session_id}:{reservoir}", 
            "-F", "#{pane_id}\t#{pane_current_command}\t#{@nexus_tab_name}"
        ]).decode().strip()
        
        if not result:
            return [fmt("Your shelf is empty.", "DISABLED", "NONE")]
            
        items = []
        for line in result.split("\n"):
            parts = line.split("\t")
            if len(parts) >= 3:
                pid, cmd, name = parts[0], parts[1], parts[2]
                label = name if name else cmd
                items.append(fmt(f"📦 {label}", "SHELF_ITEM", pid, 
                                 description=f"Stowed: {cmd}", 
                                 color="cyan"))
        return items
    except subprocess.CalledProcessError:
        return [fmt("Shelf is empty (reservoir window missing).", "DISABLED", "NONE")]
    except Exception as e:
        return [fmt(f"Shelf Error: {e}", "ERROR", "NONE")]
