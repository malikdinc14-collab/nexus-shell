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
from engine.surfaces import NullSurface


@pytest.fixture
def test_daemon():
    """Fixture to provide an isolated daemon instance with a MockTmuxAdapter."""
    daemon = NexusDaemon()
    daemon.adapter = MockTmuxAdapter()
    # Seed the mock adapter with an initial active pane
    daemon.adapter._create_pane("%1")
    daemon.adapter.focused_pane = "%1"

    # NexusCore needs a NullSurface (real TmuxSurface calls actual tmux)
    if daemon.core:
        daemon.core.surface = NullSurface()

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

    res = daemon.handle_stack_op("push", {
        "role": "editor", "pane_id": "%2", "name": "Neovim",
        "focused_id": "%1",
    })

    assert res["status"] == "ok"
    stack_id = res.get("stack_id")
    assert stack_id is not None

    # Verify via NexusCore's state (synced back to daemon)
    tabs = daemon.core.list_tabs("editor")
    assert len(tabs) == 2

    # New pane is visible/active, old pane is background
    assert tabs[1]["id"] == "%2"
    assert tabs[1]["name"] == "Neovim"
    assert tabs[1]["status"] == "VISIBLE"

    assert tabs[0]["id"] == "%1"
    assert tabs[0]["status"] == "BACKGROUND"


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

    daemon.handle_stack_op("push", {
        "role": "editor", "pane_id": "%2", "name": "P2",
        "focused_id": "%1",
    })
    daemon.adapter.focused_pane = "%2"

    daemon.handle_stack_op("push", {
        "role": "editor", "pane_id": "%3", "name": "P3",
        "focused_id": "%2",
    })
    daemon.adapter.focused_pane = "%3"

    # Currently viewing %3 (index 2)
    tabs = daemon.core.list_tabs("editor")
    assert len(tabs) == 3
    assert tabs[2]["active"] is True
    assert tabs[2]["status"] == "VISIBLE"
    assert tabs[0]["status"] == "BACKGROUND"

    # Switch to index 1
    res = daemon.handle_stack_op("switch", {
        "role": "editor", "index": 1, "focused_id": "%3",
    })

    assert res["status"] == "ok"
    tabs = daemon.core.list_tabs("editor")
    assert tabs[1]["active"] is True
    assert tabs[1]["status"] == "VISIBLE"
    assert tabs[2]["status"] == "BACKGROUND"
