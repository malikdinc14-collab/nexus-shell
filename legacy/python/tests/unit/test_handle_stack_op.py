"""Tests for NexusCore.handle_stack_op — the unified stack operation dispatcher."""

import pytest
from engine.core import NexusCore
from engine.surfaces import NullSurface
from engine.bus.typed_events import EventType


@pytest.fixture
def core():
    return NexusCore(NullSurface())


class TestStackPush:
    def test_push_creates_stack_and_tab(self, core):
        result = core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%5",
            "focused_id": "%1",
            "name": "Vim",
        })
        assert result["status"] == "ok"
        assert result["stack_id"].startswith("stack_")

        tabs = core.list_tabs("editor")
        assert len(tabs) == 2
        assert tabs[0]["name"] == "Editor"
        assert tabs[0]["status"] == "BACKGROUND"
        assert tabs[0]["active"] is False
        assert tabs[1]["name"] == "Vim"
        assert tabs[1]["status"] == "VISIBLE"
        assert tabs[1]["active"] is True

    def test_push_requires_pane_id(self, core):
        result = core.handle_stack_op("push", {
            "identity": "editor",
            "focused_id": "%1",
        })
        assert result["status"] == "error"
        assert result["error"] == "no_pane_id"

    def test_push_assigns_role(self, core):
        core.handle_stack_op("push", {
            "identity": "terminal",
            "pane_id": "%5",
            "focused_id": "%1",
        })
        sid, stack = core.stacks.get_by_identity("terminal")
        assert stack is not None
        assert stack.role == "terminal"

    def test_push_multiple_tabs(self, core):
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%5",
            "focused_id": "%1",
            "name": "Tab1",
        })
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%9",
            "name": "Tab2",
        })
        tabs = core.list_tabs("editor")
        assert len(tabs) == 3
        # Only the last pushed tab is active
        active = [t for t in tabs if t["active"]]
        assert len(active) == 1
        assert active[0]["name"] == "Tab2"


class TestStackSwitch:
    def _setup_stack(self, core):
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%5",
            "focused_id": "%1",
            "name": "Tab1",
        })
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%9",
            "name": "Tab2",
        })

    def test_switch_to_index(self, core):
        self._setup_stack(core)
        result = core.handle_stack_op("switch", {
            "identity": "editor",
            "index": 0,
        })
        assert result["status"] == "ok"
        tabs = core.list_tabs("editor")
        assert tabs[0]["active"] is True
        assert tabs[0]["status"] == "VISIBLE"
        assert tabs[1]["active"] is False
        assert tabs[2]["active"] is False

    def test_switch_already_active(self, core):
        self._setup_stack(core)
        result = core.handle_stack_op("switch", {
            "identity": "editor",
            "index": 2,  # already active after two pushes
        })
        assert result["status"] == "ok"
        assert result.get("message") == "already_active"

    def test_switch_invalid_index(self, core):
        self._setup_stack(core)
        result = core.handle_stack_op("switch", {
            "identity": "editor",
            "index": 99,
        })
        assert result["status"] == "error"

    def test_switch_nonexistent_stack(self, core):
        result = core.handle_stack_op("switch", {
            "identity": "nonexistent",
            "index": 0,
        })
        assert result["status"] == "error"


class TestStackReplace:
    def test_replace_active_tab(self, core):
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%5",
            "focused_id": "%1",
            "name": "OldTab",
        })
        result = core.handle_stack_op("replace", {
            "identity": "editor",
            "pane_id": "%9",
            "name": "NewTab",
        })
        assert result["status"] == "ok"
        tabs = core.list_tabs("editor")
        # Foundation + replaced tab = 2
        assert len(tabs) == 2
        assert tabs[1]["name"] == "NewTab"
        assert tabs[1]["id"] == "%9"

    def test_replace_nonexistent_falls_back_to_push(self, core):
        result = core.handle_stack_op("replace", {
            "identity": "newstack",
            "pane_id": "%5",
            "focused_id": "%1",
            "name": "First",
        })
        assert result["status"] == "ok"
        tabs = core.list_tabs("newstack")
        assert len(tabs) >= 1


class TestStackClose:
    def _setup_stack(self, core):
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%5",
            "focused_id": "%1",
            "name": "Overlay",
        })

    def test_close_active_tab(self, core):
        self._setup_stack(core)
        result = core.handle_stack_op("close", {"identity": "editor"})
        assert result["status"] == "ok"
        tabs = core.list_tabs("editor")
        assert len(tabs) == 1
        assert tabs[0]["status"] == "VISIBLE"
        assert tabs[0]["active"] is True

    def test_close_foundation_protected(self, core):
        self._setup_stack(core)
        # Close the overlay first
        core.handle_stack_op("close", {"identity": "editor"})
        # Now only foundation remains — close should fail
        result = core.handle_stack_op("close", {"identity": "editor"})
        assert result["status"] == "error"
        assert result["error"] == "foundation_protected"

    def test_close_empty_stack(self, core):
        result = core.handle_stack_op("close", {"identity": "nonexistent"})
        assert result["status"] == "error"


class TestStackAdopt:
    def test_adopt_creates_stack(self, core):
        result = core.handle_stack_op("adopt", {
            "identity": "terminal",
            "pane_id": "%3",
            "name": "zsh",
        })
        assert result["status"] == "ok"
        tabs = core.list_tabs("terminal")
        assert len(tabs) == 1
        assert tabs[0]["name"] == "zsh"

    def test_adopt_requires_pane_id(self, core):
        result = core.handle_stack_op("adopt", {
            "identity": "terminal",
        })
        assert result["status"] == "error"


class TestUnknownOp:
    def test_unknown_op_returns_error(self, core):
        result = core.handle_stack_op("bogus", {})
        assert result["status"] == "error"
        assert result["error"] == "unknown_op"


class TestStackEvents:
    """Verify that stack operations publish events to the bus."""

    def test_push_publishes_event(self, core):
        events = []
        core.bus.subscribe("stack.push", lambda e: events.append(e))
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%5",
            "focused_id": "%1",
        })
        assert len(events) == 1
        assert events[0].event_type == EventType.STACK_PUSH

    def test_switch_publishes_event(self, core):
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%5",
            "focused_id": "%1",
        })
        events = []
        core.bus.subscribe("stack.switch", lambda e: events.append(e))
        core.handle_stack_op("switch", {"identity": "editor", "index": 0})
        assert len(events) == 1
        assert events[0].event_type == EventType.STACK_SWITCH

    def test_close_publishes_event(self, core):
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%5",
            "focused_id": "%1",
        })
        events = []
        core.bus.subscribe("stack.close", lambda e: events.append(e))
        core.handle_stack_op("close", {"identity": "editor"})
        assert len(events) == 1
        assert events[0].event_type == EventType.STACK_CLOSE


class TestSerializationRoundTrip:
    """Verify that stack state survives serialize/deserialize."""

    def test_round_trip_preserves_state(self, core):
        core.handle_stack_op("push", {
            "identity": "editor",
            "pane_id": "%5",
            "focused_id": "%1",
            "name": "Vim",
        })
        state = core.stacks.serialize()

        core2 = NexusCore(NullSurface())
        core2.stacks.deserialize(state)

        tabs = core2.list_tabs("editor")
        assert len(tabs) == 2
        assert tabs[0]["name"] == "Editor"
        assert tabs[1]["name"] == "Vim"
