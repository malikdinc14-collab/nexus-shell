import sys
import os
import json
import random
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from importlib.machinery import SourceFileLoader

# --- Pre-Import Mocks ---
with patch("subprocess.check_output") as mock_check:
    mock_check.return_value = b"test_session"
    nexus_home = Path(__file__).parent.parent.parent
    sys.path.append(str(nexus_home / "core" / "stack"))
    stack_path = nexus_home / "core" / "stack" / "nxs-stack"
    nxs = SourceFileLoader("nxs_stack", str(stack_path)).load_module()
    sys.modules["nxs_stack"] = nxs

# --- Invariants ---

def check_invariants(state):
    for role, data in state.items():
        tabs = data.get("tabs", [])
        active_idx = data.get("active_index", 0)
        assert len(tabs) > 0, f"Role {role} has no tabs"
        if tabs[0]["name"] != "nexus-terminal":
             print(f"CRITICAL: Role {role} lost foundation. Tabs: {tabs}")
             print(f"Full State: {json.dumps(state, indent=2)}")
        assert tabs[0]["name"] == "nexus-terminal", f"Role {role} lost foundation"
        assert 0 <= active_idx < len(tabs), f"Role {role} index out of bounds"
        ids = [t["id"] for t in tabs]
        assert len(ids) == len(set(ids)), f"Role {role} duplicate IDs: {ids}"

# --- Stress Test ---

def test_random_walk_stress(tmp_path):
    """Perform 500 random operations and verify invariants at each step."""
    state_file = tmp_path / "stacks.json"
    nxs.STACK_STATE = state_file
    nxs.USER_TMP = tmp_path
    
    # Initial state
    initial_state = {
        "local": {
            "active_index": 0,
            "tabs": [{"id": "pane_0", "name": "nexus-terminal"}]
        }
    }
    state_file.write_text(json.dumps(initial_state))
    
    # Dynamic Mock for run_tmux
    pane_counter = 1
    visible_pane = "pane_0"
    
    def tmux_side_effect(args):
        nonlocal pane_counter, visible_pane
        if "split-window" in args:
            pid = f"pane_{pane_counter}"
            pane_counter += 1
            return pid
        if "#{pane_id}" in args:
            return visible_pane
        if "#{@nexus_role}" in args:
            return "local"
        if "swap-pane" in args:
            # Reorder args to find new_pane_id (-t) and visible_pane (-s)
            # This is hard to track perfectly, but we just return success
            return "true"
        return "true"

    with patch.object(nxs, "run_tmux") as mock_tmux:
        mock_tmux.side_effect = tmux_side_effect
        
        ops = ["push", "switch", "close", "replace"]
        
        for i in range(500):
            op = random.choice(ops)
            state = nxs.load_state()
            role = "test_slot"
            
            # Helper to ensure role exists for test maintenance
            if role not in state:
                nxs.push(role, "foundation_cmd", "nexus-terminal")
                state = nxs.load_state()

            try:
                if op == "push":
                    nxs.push(role, f"cmd_{i}", f"Tool_{i}")
                elif op == "switch":
                    tabs = state[role]["tabs"]
                    idx = random.randint(0, len(tabs) - 1)
                    nxs.switch_to(role, idx)
                elif op == "close":
                    nxs.close_tab(role)
                elif op == "replace":
                    nxs.replace(role, f"replaced_{i}", f"Replaced_{i}")
                
                # Update visible_pane mock based on current state
                state = nxs.load_state()
                if role in state:
                     print(f"STEP {i} {op}: {[t['name'] for t in state[role]['tabs']]}")
                     visible_pane = state[role]["tabs"][state[role]["active_index"]]["id"]
                else:
                     print(f"STEP {i} {op}: ROLE KILLED")
            except Exception as e:
                # Provide much more context on failure
                print(f"FAILED AT STEP {i} OP {op}")
                print(f"State: {json.dumps(state, indent=2)}")
                raise
            
            # Check Invariants after every step
            new_state = nxs.load_state()
            check_invariants(new_state)

    print(f"Successfully completed 500 random operations on nxs-stack.")
