#!/usr/bin/env python3
# core/engine/api/control_bridge.py
import os
import sys
import subprocess
from pathlib import Path

class ControlBridge:
    def __init__(self):
        self.nexus_home = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[3]))
        self.nexus_state = Path(os.environ.get("NEXUS_STATE", f"/tmp/nexus_{os.getlogin()}"))
        self.session_name = self._get_tmux_session()

    def _get_tmux_session(self):
        try:
            return subprocess.check_output(["tmux", "display-message", "-p", "#S"], stderr=subprocess.DEVNULL).decode().strip()
        except:
            return "nexus_default"

    def get_nvim_pipe(self):
        project_name = self.session_name.replace("nexus_", "")
        pipe = self.nexus_state / f"pipes/nvim_{project_name}.pipe"
        return pipe if pipe.exists() else None

    def send_to_editor(self, command):
        """Sends a command to the running Neovim instance if it exists."""
        pipe = self.get_nvim_pipe()
        if not pipe:
            return False, "No running editor instance found."
        
        try:
            # Add <CR> if it's a colon command and missing it
            if command.startswith(":") and not command.endswith("<CR>"):
                command += "<CR>"
            
            subprocess.run(["nvim", "--server", str(pipe), "--remote-send", command], check=True)
            return True, "Command sent to editor."
        except Exception as e:
            return False, f"Failed to send to editor: {e}"

    def send_to_role(self, role, command):
        """Sends keys to a tmux pane associated with a specific role."""
        try:
            # Find the first pane matching the role
            target = subprocess.check_output(
                ["tmux", "list-panes", "-a", "-F", "#{pane_id} #{@nexus_role}"],
                stderr=subprocess.DEVNULL
            ).decode().splitlines()
            
            pane_id = next((line.split()[0] for line in target if role in line), None)
            
            if not pane_id:
                return False, f"No pane found for role: {role}"
            
            subprocess.run(["tmux", "send-keys", "-t", pane_id, command, "Enter"], check=True)
            return True, f"Sent keys to {role} pane ({pane_id})."
        except Exception as e:
            return False, f"Tmux control error: {e}"

if __name__ == "__main__":
    bridge = ControlBridge()
    if len(sys.argv) < 3:
        print("Usage: control_bridge.py <target> <command>")
        sys.exit(1)
    
    target = sys.argv[1]
    cmd = sys.argv[2]
    
    if target == "editor":
        success, msg = bridge.send_to_editor(cmd)
    else:
        success, msg = bridge.send_to_role(target, cmd)
    
    print(msg)
    sys.exit(0 if success else 1)
