"""
Unit tests for Tab, TabStack, and TabReservoir data models.
Covers T010 (Tab/TabStack) and T011 (TabReservoir).
"""
import sys
import os
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core"))

os.environ.setdefault("NEXUS_HOME", "/tmp/mock_nexus_home")

from engine.stacks.stack import Tab, TabStack
from engine.stacks.reservoir import TabReservoir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tab(**overrides) -> Tab:
    """Factory for Tab instances with sensible defaults."""
    defaults = {
        "capability_type": "editor",
        "adapter_name": "neovim",
        "command": "nvim",
        "cwd": "/tmp",
    }
    defaults.update(overrides)
    return Tab(**defaults)


def make_stack(n_tabs: int = 0, **overrides) -> TabStack:
    """Factory for TabStack. Optionally pre-populate with n_tabs tabs."""
    defaults = {"pane_id": "%1"}
    defaults.update(overrides)
    stack = TabStack(**defaults)
    for i in range(n_tabs):
        stack.push(make_tab(adapter_name=f"tab-{i}"))
    return stack


# ---------------------------------------------------------------------------
# Tab basics
# ---------------------------------------------------------------------------

class TestTab:
    def test_tab_gets_uuid_id(self):
        tab = make_tab()
        assert tab.id  # non-empty string
        assert isinstance(tab.id, str)

    def test_tab_defaults(self):
        tab = make_tab()
        assert tab.tmux_pane_id is None
        assert tab.is_active is False
        assert tab.native_multiplicity is False
        assert tab.env == {}
        assert tab.role is None

    def test_tab_mutable_defaults_are_independent(self):
        t1 = make_tab()
        t2 = make_tab()
        t1.env["FOO"] = "bar"
        assert "FOO" not in t2.env


# ---------------------------------------------------------------------------
# TabStack — active_tab property
# ---------------------------------------------------------------------------

class TestActiveTab:
    def test_active_tab_on_empty_stack(self):
        stack = make_stack()
        assert stack.active_tab is None

    def test_active_tab_returns_correct_tab(self):
        stack = make_stack(n_tabs=3)
        assert stack.active_tab is stack.tabs[stack.active_index]
        assert stack.active_tab.is_active is True


# ---------------------------------------------------------------------------
# TabStack.push
# ---------------------------------------------------------------------------

class TestPush:
    def test_push_onto_empty_stack(self):
        stack = make_stack()
        tab = make_tab(adapter_name="neovim")
        stack.push(tab)

        assert len(stack.tabs) == 1
        assert stack.active_index == 0
        assert tab.is_active is True
        assert stack.active_tab is tab

    def test_push_onto_stack_with_existing_tabs(self):
        stack = make_stack(n_tabs=2)
        old_active = stack.active_tab

        new_tab = make_tab(adapter_name="zsh")
        stack.push(new_tab)

        assert len(stack.tabs) == 3
        assert stack.active_tab is new_tab
        assert new_tab.is_active is True
        assert old_active.is_active is False

    def test_push_sets_pane_id_on_tab(self):
        stack = make_stack(pane_id="%5")
        tab = make_tab()
        stack.push(tab)
        assert tab.tmux_pane_id == "%5"


# ---------------------------------------------------------------------------
# TabStack.pop
# ---------------------------------------------------------------------------

class TestPop:
    def test_pop_with_multiple_tabs_reveals_next(self):
        stack = make_stack(n_tabs=3)
        # active_index should be 2 (last pushed)
        popped = stack.pop()

        assert popped is not None
        assert popped.is_active is False
        assert popped.tmux_pane_id is None
        assert len(stack.tabs) == 2
        # After popping last, active wraps to valid index
        assert stack.active_tab is not None
        assert stack.active_tab.is_active is True

    def test_pop_last_tab_empties_stack(self):
        stack = make_stack(n_tabs=1)
        popped = stack.pop()

        assert popped is not None
        assert len(stack.tabs) == 0
        assert stack.active_tab is None
        assert stack.active_index == 0

    def test_pop_on_empty_stack_returns_none(self):
        stack = make_stack()
        assert stack.pop() is None

    def test_pop_detaches_tab(self):
        stack = make_stack(n_tabs=2)
        popped = stack.pop()
        assert popped.tmux_pane_id is None
        assert popped.is_active is False


# ---------------------------------------------------------------------------
# TabStack.rotate
# ---------------------------------------------------------------------------

class TestRotate:
    def test_rotate_forward(self):
        stack = make_stack(n_tabs=3)
        # After 3 pushes, active_index == 2
        old_active = stack.active_tab

        stack.rotate(1)

        assert stack.active_index == 0  # wraps around
        assert stack.active_tab is stack.tabs[0]
        assert stack.active_tab.is_active is True
        assert old_active.is_active is False

    def test_rotate_backward(self):
        stack = make_stack(n_tabs=3)
        # active_index == 2
        stack.rotate(-1)

        assert stack.active_index == 1
        assert stack.active_tab is stack.tabs[1]
        assert stack.active_tab.is_active is True

    def test_rotate_wraps_backward_from_zero(self):
        stack = make_stack(n_tabs=3)
        # Move to index 0 first
        stack.rotate(1)
        assert stack.active_index == 0

        stack.rotate(-1)
        assert stack.active_index == 2

    def test_rotate_single_tab_is_noop(self):
        stack = make_stack(n_tabs=1)
        active_before = stack.active_tab
        idx_before = stack.active_index

        stack.rotate(1)

        assert stack.active_index == idx_before
        assert stack.active_tab is active_before
        assert active_before.is_active is True

    def test_rotate_empty_stack_is_noop(self):
        stack = make_stack()
        stack.rotate(1)
        assert stack.active_index == 0
        assert stack.active_tab is None


# ---------------------------------------------------------------------------
# TabReservoir
# ---------------------------------------------------------------------------

class TestReservoir:
    def test_shelve_detaches_tab(self):
        reservoir = TabReservoir()
        tab = make_tab(tmux_pane_id="%3", is_active=True)

        reservoir.shelve(tab)

        assert tab.tmux_pane_id is None
        assert tab.is_active is False
        assert tab in reservoir.tabs

    def test_recall_returns_tab_and_sets_pane(self):
        reservoir = TabReservoir()
        tab = make_tab()
        reservoir.shelve(tab)
        tab_id = tab.id

        recalled = reservoir.recall(tab_id, target_pane_id="%7")

        assert recalled is tab
        assert recalled.tmux_pane_id == "%7"
        assert tab not in reservoir.tabs

    def test_recall_nonexistent_returns_none(self):
        reservoir = TabReservoir()
        assert reservoir.recall("no-such-id", "%1") is None

    def test_shelve_recall_lifecycle(self):
        """Full lifecycle: create -> shelve -> recall -> verify state."""
        reservoir = TabReservoir()

        tab = make_tab(tmux_pane_id="%2", is_active=True, cwd="/home/user")
        original_id = tab.id

        # Shelve
        reservoir.shelve(tab)
        assert len(reservoir.tabs) == 1
        assert tab.tmux_pane_id is None
        assert tab.is_active is False

        # Recall
        recalled = reservoir.recall(original_id, "%9")
        assert recalled is not None
        assert recalled.id == original_id
        assert recalled.tmux_pane_id == "%9"
        assert recalled.cwd == "/home/user"  # preserved
        assert len(reservoir.tabs) == 0

    def test_reservoir_mutable_default(self):
        r1 = TabReservoir()
        r2 = TabReservoir()
        r1.shelve(make_tab())
        assert len(r2.tabs) == 0
