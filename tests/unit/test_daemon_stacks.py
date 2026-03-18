import sys
import os
import pytest
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "core"))

# Mock environment to avoid state engine triggering file loads
os.environ["NEXUS_HOME"] = "/tmp/mock_nexus_home"

from services.internal.daemon import NexusDaemon, MockTmuxAdapter

@pytest.fixture
def test_daemon():
    """Fixture to provide an isolated daemon instance with a MockTmuxAdapter."""
    daemon = NexusDaemon()
    daemon.adapter = MockTmuxAdapter()
    # Seed the mock adapter with an initial active pane
    daemon.adapter._create_pane("%1")
    daemon.adapter.focused_pane = "%1"
    
    # Setup initial anonymous state matching REQ-01
    daemon.state["stacks"] = {}
    
    return daemon

def test_push_increments_active_index(test_daemon):
    """
    REQ-14/15: 'push' command must properly append the tab to the stack
    and increment the active_index, modifying the visible/background state.
    """
    daemon = test_daemon
    
    # Spawning a new pane (like `Alt-N`) produces pane "%2". 
    daemon.adapter._create_pane("%2")
    
    res = daemon._op_push("editor", {"pane_id": "%2", "name": "Neovim"})
    
    assert res["status"] == "ok"
    stack_id = res.get("stack_id")
    assert stack_id is not None
    
    stack = daemon.state["stacks"][stack_id]
    
    # Foundation pane "%1" + New pane "%2"
    assert len(stack["tabs"]) == 2
    assert stack["active_index"] == 1
    
    # New pane is visible, old pane is pushed to background
    assert stack["tabs"][1]["id"] == "%2"
    assert stack["tabs"][1]["name"] == "Neovim"
    assert stack["tabs"][1]["status"] == "VISIBLE"
    
    assert stack["tabs"][0]["id"] == "%1"
    assert stack["tabs"][0]["status"] == "BACKGROUND"

def test_rotate_tabs(test_daemon):
    """
    REQ-07: Users must be able to rotate through the tabs.
    Rotations updates logical VISIBLE/BACKGROUND states.
    """
    daemon = test_daemon
    
    # Setup 3 panes
    daemon.adapter._create_pane("%1")
    daemon.adapter._create_pane("%2")
    daemon.adapter._create_pane("%3")
    daemon.adapter.focused_pane = "%1"
    
    daemon._op_push("editor", {"pane_id": "%2", "name": "P2"})
    daemon.adapter.focused_pane = "%2"
    
    daemon._op_push("editor", {"pane_id": "%3", "name": "P3"})
    daemon.adapter.focused_pane = "%3"
    
    stack_id, stack = daemon._get_or_create_stack("editor")
    
    # Currently viewing %3
    assert stack["active_index"] == 2
    assert stack["tabs"][2]["status"] == "VISIBLE"
    assert stack["tabs"][0]["status"] == "BACKGROUND"
    
    # Rotate backward
    daemon.adapter.focused_pane = "%3"
    print(f"\n[DEBUG] Before Switch State: {daemon.state['stacks']}")
    res = daemon._op_switch("editor", {"index": 1})
    print(f"\n[DEBUG] After Switch State: {daemon.state['stacks']}")
    
    assert res["status"] == "ok"
    assert stack["active_index"] == 1
    assert stack["tabs"][1]["status"] == "VISIBLE"
    assert stack["tabs"][2]["status"] == "BACKGROUND"
