#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

from pathlib import Path as _Path
_ENGINE_ROOT = _Path(__file__).resolve().parents[2]  # core/kernel/stack -> core
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

try:
    from engine.actions.resolver import AdapterResolver
    _MUX = AdapterResolver.multiplexer()
except Exception:
    _MUX = None

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
    """Fetches identity hints from the container via adapter."""
    ids = {}
    if _MUX is None:
        return ids
    for key in ["nexus_role", "nexus_stack_id"]:
        val = _MUX.get_tag(pane_id, key)
        if val and val != "null":
            ids[f"@{key}"] = val
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
    state = load_state()
    registry = state.get("stacks", {})

    # Resolve the Stack by finding which stack contains this pane_id.
    # This is stable across swap-pane operations — the pane_id travels
    # with the content, and the registry tracks all tab pane IDs.
    found_sid, stack = None, None
    for sid, sdata in registry.items():
        for tab in sdata.get("tabs", []):
            if tab.get("id") == pane_id:
                found_sid, stack = sid, sdata
                break
        if stack:
            break

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
