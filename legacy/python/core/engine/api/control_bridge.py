#!/usr/bin/env python3
# core/engine/api/control_bridge.py
import os
import sys
from pathlib import Path

# Ensure engine is importable
_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from engine.actions.resolver import AdapterResolver

class ControlBridge:
    def __init__(self):
        self.nexus_home = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[3]))
        self.nexus_state = Path(os.environ.get("NEXUS_STATE", f"/tmp/nexus_{os.getlogin()}"))
        self.session_name = self._get_tmux_session()

    def _get_tmux_session(self):
        return os.environ.get("NEXUS_SESSION", "nexus_default")

    def get_nvim_pipe(self):
        project_name = self.session_name.replace("nexus_", "")
        pipe = self.nexus_state / f"pipes/nvim_{project_name}.pipe"
        return pipe if pipe.exists() else None

    def send_to_editor(self, command):
        """Sends a command to the running Neovim instance via EditorCapability adapter."""
        # Add <CR> if it's a colon command and missing it
        if command.startswith(":") and not command.endswith("<CR>"):
            command += "<CR>"

        editor = AdapterResolver.editor()
        success = editor.send_editor_command(command)
        if success:
            return True, "Command sent to editor."
        return False, "No running editor instance found."

    def send_to_role(self, role, command):
        """Sends keys to a tmux pane associated with a specific role."""
        try:
            mux = AdapterResolver.multiplexer()

            # Find the first pane matching the role
            raw = mux._run(["list-panes", "-a", "-F", "#{pane_id} #{@nexus_role}"])
            lines = raw.splitlines() if raw else []

            pane_id = next((line.split()[0] for line in lines if role in line), None)

            if not pane_id:
                return False, f"No pane found for role: {role}"

            mux.send_command(pane_id, command)
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
