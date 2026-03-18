#!/usr/bin/env python3
# core/engine/state/state_engine.py
import json
import os
import sys
from pathlib import Path
from datetime import datetime

class NexusStateEngine:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or os.getcwd()).resolve()
        
        # 1. Primary: Project-local
        self.state_dir = self.project_root / ".nexus"
        self.state_file = self.state_dir / "state.json"
        
        # 2. Secondary: User-local Fallback (if project root is restricted)
        import hashlib
        proj_hash = hashlib.md5(str(self.project_root).encode()).hexdigest()[:10]
        self.fallback_dir = Path.home() / ".nexus" / "storage" / proj_hash
        self.fallback_file = self.fallback_dir / "state.json"
        
        self.active_file = self.state_file
        self.state = {}
        self.load()

    def load(self):
        # Axiom: Try primary, fallback to secondary on any permission/system error
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                    self.active_file = self.state_file
                    return
        except (PermissionError, OSError):
            pass
            
        try:
            if self.fallback_file.exists():
                with open(self.fallback_file, 'r') as f:
                    self.state = json.load(f)
                    self.active_file = self.fallback_file
                    return
        except:
            pass
            
        # Initial State if no file found or accessible
        self.state = {
            "project": {"name": self.project_root.name, "path": str(self.project_root)},
            "ui": {"slots": {}, "stacks": {}},
            "context": {"last_opened_files": []}
        }
        # If project dir is not writable, the FIRST save will pivot to fallback
        if not os.access(self.state_dir, os.W_OK) if self.state_dir.exists() else not os.access(self.project_root, os.W_OK):
            self.active_file = self.fallback_file

    def save(self):
        target_file = self.active_file
        target_dir = target_file.parent
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            with open(target_file, 'w') as f:
                json.dump(self.state, f, indent=4)
        except (PermissionError, OSError) as e:
            # If primary save fails, pivot to fallback forever for this session
            if target_file == self.state_file:
                self.active_file = self.fallback_file
                self.save()
            else:
                print(f"CRITICAL: State Engine failed to save to {target_file}: {e}", file=sys.stderr)

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
