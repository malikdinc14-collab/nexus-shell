#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

import getpass
USER_TMP = Path(f"/tmp/nexus_{getpass.getuser()}")
STACK_STATE = USER_TMP / "stacks.json"
DEBUG_MODE_FILE = USER_TMP / "debug_pane_ids"

# State Handshake
sys.path.append(str(Path(__file__).resolve().parent.parent / "state"))
try:
    from state_engine import NexusStateEngine
except ImportError:
    NexusStateEngine = None

def get_engine():
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    if NexusStateEngine:
        return NexusStateEngine(project_root)
    return None

def load_state():
    engine = get_engine()
    if engine:
        return engine.get("ui.stacks") or {}
    return {}


def get_identity_metadata(pane_id):
    """Fetches identity hints from the container."""
    import subprocess
    ids = {}
    for key in ["@nexus_role", "@nexus_stack_id"]:
        try:
            val = subprocess.check_output(["tmux", "display-message", "-p", "-t", pane_id, f"#{{{key}}}"]).decode().strip()
            if val and val != "null": ids[key] = val
        except: pass
    return ids

def main():
    if len(sys.argv) < 2:
        return

    pane_id = sys.argv[1]

    # 1. Check for Neovim First (Hybrid Mode)
    nv_data = get_nvim_tabs(pane_id)
    if nv_data:
        output = []
        for i, name in enumerate(nv_data["tabs"]):
            idx = i + 1
            display_name = os.path.basename(name) if name else "[No Name]"
            if idx == nv_data["current"]:
                output.append(f"#[fg=cyan,bold][ {display_name} ]")
            else:
                output.append(f"#[fg=white,dim] {display_name} ")
        print(" ".join(output))
        return

    # 2. Nexus Stack Mode
    meta = get_identity_metadata(pane_id)
    role = meta.get("@nexus_role")
    sid_hint = meta.get("@nexus_stack_id")
    
    state = load_state()
    registry = state.get("stacks", {})
    
    # Resolve the Stack
    found_sid, stack = None, None
    
    # Priority 1: Direct UUID match
    if sid_hint in registry:
        found_sid, stack = sid_hint, registry[sid_hint]
    # Priority 2: Role match
    elif role:
        for sid, sdata in registry.items():
            if sdata.get("role") == role:
                found_sid, stack = sid, sdata; break
    # Priority 3: Pane ID fallback (Anonymous Stack)
    if not stack and pane_id in registry:
        found_sid, stack = pane_id, registry[pane_id]

    if not stack or not stack.get("tabs"):
        label = role if role else (sid_hint if sid_hint else pane_id)
        # Shorthand for UUIDs
        if label.startswith("stack_"): label = f"[{label[:12]}]"
        print(f"#[fg=yellow,bold]{label}#[default]")
        return

    tabs = stack["tabs"]
    active_idx = stack["active_index"]
    
    # Header: Role or Shorthand Stack ID
    header = role if role else f"[{found_sid[:12]}]"
    output = [f"#[fg=yellow,bold]{header}#[default]"]
    
    for i, tab in enumerate(tabs):
        name = tab["name"]
        if i == active_idx:
            output.append(f"#[fg=cyan,bold][ {name} ]")
        else:
            output.append(f"#[fg=white,dim] {name} ")

    print(" ".join(output))


if __name__ == "__main__":
    main()
