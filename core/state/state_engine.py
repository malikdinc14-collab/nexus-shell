#!/usr/bin/env python3
# core/state/state_engine.py
import json
import os
import sys
from pathlib import Path
from datetime import datetime

class NexusStateEngine:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or os.getcwd())
        self.state_dir = self.project_root / ".nexus"
        self.state_file = self.state_dir / "state.json"
        self.state = {}
        self.load()

    def load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
            except:
                self.state = {}
        else:
            self.state = {
                "project": {"name": self.project_root.name},
                "ui": {"slots": {}},
                "context": {"last_opened_files": []}
            }

    def save(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=4)

    def get(self, path):
        keys = path.split('.')
        curr = self.state
        for k in keys:
            if isinstance(curr, dict):
                curr = curr.get(k, None)
            else:
                return None
        return curr

    def set(self, path, value):
        keys = path.split('.')
        curr = self.state
        for k in keys[:-1]:
            if k not in curr or not isinstance(curr[k], dict):
                curr[k] = {}
            curr = curr[k]
        
        # Automatic type conversion for common strings
        if isinstance(value, str):
            if value.lower() == 'true': value = True
            elif value.lower() == 'false': value = False
            elif value.isdigit(): value = int(value)
            
        curr[keys[-1]] = value
        self.save()

    def update_slot(self, slot_name, tool_name):
        """Updates the tool assigned to a specific UI slot."""
        self.set(f"ui.slots.{slot_name}.tool", tool_name)

    def update_session(self, session_data):
        """Pushes full tmux session state into the project manifest."""
        if "session" not in self.state: self.state["session"] = {}
        self.state["session"]["last_save"] = datetime.now().isoformat()
        self.state["session"]["layout"] = session_data
        self.save()

    def get_session(self):
        return self.get("session.layout")

if __name__ == "__main__":
    engine = NexusStateEngine()
    if len(sys.argv) > 2:
        action = sys.argv[1]
        path = sys.argv[2]
        if action == "get":
            print(json.dumps(engine.get(path)) if engine.get(path) is not None else "")
        elif action == "set":
            engine.set(path, sys.argv[3])
