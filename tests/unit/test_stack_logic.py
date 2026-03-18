import sys
import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
from importlib.machinery import SourceFileLoader

# --- Pre-Import Mocks ---

# Pre-emptively mock subprocess to prevent nxs-stack from hanging during import
with patch("subprocess.check_output") as mock_check:
    mock_check.return_value = b"test_session"
    
    # Add core/kernel/stack to path to import nxs-stack
    nexus_home = Path(__file__).parent.parent.parent
    sys.path.append(str(nexus_home / "core" / "stack"))

    # Dynamic import of nxs-stack as it doesn't have a .py extension
    stack_path = nexus_home / "core" / "stack" / "nxs-stack"
    nxs = SourceFileLoader("nxs_stack", str(stack_path)).load_module()
    sys.modules["nxs_stack"] = nxs

# --- Invariants ---

def check_invariants(state):
    """Axiom: All state transitions must preserve these truths."""
    for role, data in state.items():
        tabs = data.get("tabs", [])
        active_idx = data.get("active_index", 0)
        
        # 1. Foundation Invariant: Index 0 must be nexus-terminal
        assert len(tabs) > 0, f"Role {role} has no tabs"
        assert tabs[0]["name"] == "nexus-terminal", f"Role {role} lost its foundation at index 0"
        
        # 2. Index Bounds Invariant
        assert 0 <= active_idx < len(tabs), f"Role {role} has out-of-bounds active_index {active_idx}"
        
        # 3. Identity Integrity
        pane_ids = [t["id"] for t in tabs]
        # We allow duplicate IDs only if they are the SAME tab, but wait...
        # In a stack, each tab SHOULD be a unique pane in the reservoir.
        assert len(pane_ids) == len(set(pane_ids)), f"Role {role} has duplicate pane IDs in stack: {pane_ids}"

# --- Mocks ---

@pytest.fixture
def mock_state(tmp_path):
    """Provides a fresh stack state in a temporary directory."""
    state_file = tmp_path / "stacks.json"
    nxs.STACK_STATE = state_file
    nxs.USER_TMP = tmp_path
    
    initial_state = {
        "local": {
            "active_index": 0,
            "tabs": [{"id": "%1", "name": "nexus-terminal"}]
        }
    }
    state_file.write_text(json.dumps(initial_state))
    return initial_state

@pytest.fixture
def mock_tmux(mock_state):
    # We patch inside the module namespace for nxs
    with patch.object(nxs, "run_tmux") as mock:
        # Default behavior for discovery calls
        def tmux_side_effect(args):
            if "split-window" in args: return "%2"
            if "#{pane_id}" in args: return "%1"
            if "#{@nexus_role}" in args: return "local"
        
        mock.side_effect = tmux_side_effect
        yield mock

# --- Tests ---

def test_push_invariant_preserved(mock_state, mock_tmux):
    """Verify that pushing a new tab preserves invariants."""
    # Ensure role resolution works: local -> focused_id=local
    nxs.push("local", "nvim", "Editor")
    
    state = nxs.load_state()
    check_invariants(state)
    
    # It should have identified 'local' since we mocked @nexus_role to return 'local'
    assert len(state["local"]["tabs"]) == 2
    assert state["local"]["tabs"][1]["name"] == "Editor"
    assert state["local"]["active_index"] == 1

def test_close_tab_foundation_protection(mock_state, mock_tmux):
    """Axiom: Cannot close the foundation tab (Index 0)."""
    # Setup: mock visible pane to be %1
    nxs.close_tab("local")
    
    # Since it was index 0, it should have triggered tmux kill-pane for the foundation
    mock_tmux.assert_any_call(["kill-pane", "-t", "%1"])

def test_close_tab_rotate(mock_state, mock_tmux):
    """Verify that closing a non-foundation tab rotates to the next."""
    # Setup: 2 tabs
    state = nxs.load_state()
    state["local"]["tabs"].append({"id": "%2", "name": "Editor"})
    state["local"]["active_index"] = 1
    nxs.save_state(state)
    
    # Mock pane_id to be %2 (the one being closed)
    def tmux_side_effect(args):
        if "#{pane_id}" in args: return "%2"
        if "#{@nexus_role}" in args: return "local"
        if "#{window_name}" in args: return "NOT_RESERVOIR"
        return "true"
    mock_tmux.side_effect = tmux_side_effect
    
    nxs.close_tab("local")
    
    new_state = nxs.load_state()
    check_invariants(new_state)
    assert len(new_state["local"]["tabs"]) == 1
    assert new_state["local"]["tabs"][0]["name"] == "nexus-terminal"
    assert new_state["local"]["active_index"] == 0

def test_stack_drift_self_healing(mock_state, mock_tmux):
    """Verify that system prunes dead panes on switch."""
    # Setup: 2 tabs, but %2 is 'dead'
    state = nxs.load_state()
    state["local"]["tabs"].append({"id": "%2", "name": "DeadTool"})
    nxs.save_state(state)
    
    # Mock pane_exists to fail for %2
    with patch.object(nxs, "pane_exists") as mock_exists:
        mock_exists.side_effect = lambda pid: pid == "%1"
        
        nxs.switch_to("local", 1)
        
        new_state = nxs.load_state()
        check_invariants(new_state)
        # Should have pruned %2 and fallen back to %1 (index 0)
        assert len(new_state["local"]["tabs"]) == 1
        assert new_state["local"]["active_index"] == 0
        assert new_state["local"]["tabs"][0]["id"] == "%1"
