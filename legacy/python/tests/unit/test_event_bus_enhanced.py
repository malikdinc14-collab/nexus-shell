"""Tests for T060-T064: typed events, enhanced bus, bus handler, and event history."""

import importlib.util
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load_module(name, rel_path):
    if name in sys.modules:
        return sys.modules[name]
    full = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

typed_mod = _load_module("engine.bus.typed_events", "core/engine/bus/typed_events.py")
bus_mod = _load_module("engine.bus.enhanced_bus", "core/engine/bus/enhanced_bus.py")
handler_mod = _load_module("engine.bus.api_handler", "core/engine/api/bus_handler.py")

EventType = typed_mod.EventType
TypedEvent = typed_mod.TypedEvent
create_event = typed_mod.create_event
EnhancedBus = bus_mod.EnhancedBus

handle_publish = handler_mod.handle_publish
handle_subscribe = handler_mod.handle_subscribe
handle_list_subscribers = handler_mod.handle_list_subscribers
handle_history = handler_mod.handle_history
set_bus = handler_mod.set_bus


# ===========================================================================
# T060 — Typed event definitions
# ===========================================================================


class TestEventType:
    def test_all_enum_values_exist(self):
        expected = [
            "STACK_PUSH", "STACK_POP", "STACK_ROTATE",
            "PANE_SPLIT", "PANE_KILL",
            "TAB_SWITCH",
            "PROFILE_SWITCH",
            "PACK_ENABLE", "PACK_DISABLE",
            "CONFIG_RELOAD",
            "COMPOSITION_SWITCH",
            "WORKSPACE_SAVE", "WORKSPACE_RESTORE",
            "CUSTOM",
        ]
        for name in expected:
            assert hasattr(EventType, name), f"Missing EventType.{name}"

    def test_enum_values_are_dotted_strings(self):
        for et in EventType:
            assert "." in et.value or et == EventType.CUSTOM

    def test_enum_count(self):
        assert len(EventType) == 24


class TestTypedEvent:
    def test_create_basic(self):
        e = TypedEvent(event_type=EventType.STACK_PUSH, source="test")
        assert e.event_type == EventType.STACK_PUSH
        assert e.source == "test"
        assert e.payload == {}
        assert isinstance(e.timestamp, float)

    def test_create_with_payload(self):
        e = TypedEvent(
            event_type=EventType.PANE_SPLIT,
            source="cli",
            payload={"direction": "vertical"},
        )
        assert e.payload["direction"] == "vertical"

    def test_timestamp_default(self):
        before = time.time()
        e = TypedEvent(event_type=EventType.CUSTOM, source="x")
        after = time.time()
        assert before <= e.timestamp <= after

    def test_create_event_convenience(self):
        e = create_event(EventType.CONFIG_RELOAD, "daemon", reason="manual")
        assert e.event_type == EventType.CONFIG_RELOAD
        assert e.source == "daemon"
        assert e.payload == {"reason": "manual"}


# ===========================================================================
# T061 — EnhancedBus: subscribe / publish / unsubscribe
# ===========================================================================


class TestEnhancedBusBasic:
    def test_subscribe_and_publish(self):
        bus = EnhancedBus()
        received = []
        bus.subscribe("stack.push", received.append)
        evt = create_event(EventType.STACK_PUSH, "test")
        count = bus.publish(evt)
        assert count == 1
        assert len(received) == 1
        assert received[0] is evt

    def test_unsubscribe(self):
        bus = EnhancedBus()
        received = []
        bus.subscribe("stack.push", received.append)
        bus.unsubscribe("stack.push", received.append)
        bus.publish(create_event(EventType.STACK_PUSH, "test"))
        assert received == []

    def test_publish_no_subscribers(self):
        bus = EnhancedBus()
        count = bus.publish(create_event(EventType.STACK_POP, "test"))
        assert count == 0

    def test_multiple_subscribers(self):
        bus = EnhancedBus()
        r1, r2 = [], []
        bus.subscribe("stack.push", r1.append)
        bus.subscribe("stack.push", r2.append)
        bus.publish(create_event(EventType.STACK_PUSH, "test"))
        assert len(r1) == 1
        assert len(r2) == 1

    def test_subscriber_count(self):
        bus = EnhancedBus()
        bus.subscribe("stack.*", lambda e: None)
        bus.subscribe("pane.*", lambda e: None)
        assert bus.subscriber_count == 2

    def test_subscriber_count_empty(self):
        bus = EnhancedBus()
        assert bus.subscriber_count == 0


# ===========================================================================
# T061 — Wildcard pattern matching
# ===========================================================================


class TestWildcardMatching:
    def test_exact_match(self):
        assert EnhancedBus._match_pattern("stack.push", "stack.push") is True

    def test_no_match(self):
        assert EnhancedBus._match_pattern("stack.push", "stack.pop") is False

    def test_star_suffix(self):
        assert EnhancedBus._match_pattern("stack.*", "stack.push") is True
        assert EnhancedBus._match_pattern("stack.*", "stack.pop") is True
        assert EnhancedBus._match_pattern("stack.*", "pane.kill") is False

    def test_star_prefix(self):
        assert EnhancedBus._match_pattern("*.push", "stack.push") is True
        assert EnhancedBus._match_pattern("*.push", "queue.push") is True
        assert EnhancedBus._match_pattern("*.push", "stack.pop") is False

    def test_double_star(self):
        assert EnhancedBus._match_pattern("*.*", "stack.push") is True
        assert EnhancedBus._match_pattern("*.*", "pane.kill") is True

    def test_wildcard_publish_delivery(self):
        bus = EnhancedBus()
        received = []
        bus.subscribe("stack.*", received.append)
        bus.publish(create_event(EventType.STACK_PUSH, "test"))
        bus.publish(create_event(EventType.STACK_POP, "test"))
        bus.publish(create_event(EventType.PANE_KILL, "test"))
        assert len(received) == 2

    def test_prefix_wildcard_delivery(self):
        bus = EnhancedBus()
        received = []
        bus.subscribe("*.switch", received.append)
        bus.publish(create_event(EventType.TAB_SWITCH, "test"))
        bus.publish(create_event(EventType.PROFILE_SWITCH, "test"))
        bus.publish(create_event(EventType.COMPOSITION_SWITCH, "test"))
        bus.publish(create_event(EventType.STACK_PUSH, "test"))
        assert len(received) == 3


# ===========================================================================
# T061 — Dead subscriber detection
# ===========================================================================


class TestDeadSubscriberDetection:
    def _bad_callback(self, event):
        raise RuntimeError("always fails")

    def test_dead_after_three_failures(self):
        bus = EnhancedBus()
        bus.subscribe("stack.push", self._bad_callback)
        for _ in range(3):
            bus.publish(create_event(EventType.STACK_PUSH, "test"))
        assert len(bus.dead_subscribers) == 1

    def test_not_dead_before_threshold(self):
        bus = EnhancedBus()
        bus.subscribe("stack.push", self._bad_callback)
        bus.publish(create_event(EventType.STACK_PUSH, "test"))
        bus.publish(create_event(EventType.STACK_PUSH, "test"))
        assert len(bus.dead_subscribers) == 0

    def test_dead_subscriber_stops_receiving(self):
        bus = EnhancedBus()
        call_count = [0]

        def flaky(event):
            call_count[0] += 1
            raise ValueError("boom")

        bus.subscribe("stack.push", flaky)
        for _ in range(5):
            bus.publish(create_event(EventType.STACK_PUSH, "test"))
        # Should have been called 3 times then marked dead
        assert call_count[0] == 3

    def test_success_resets_failure_count(self):
        bus = EnhancedBus()
        counter = [0]

        def sometimes_fails(event):
            counter[0] += 1
            if counter[0] % 3 == 0:
                raise ValueError("oops")

        bus.subscribe("stack.push", sometimes_fails)
        for _ in range(9):
            bus.publish(create_event(EventType.STACK_PUSH, "test"))
        # Failures are not consecutive so never reaches threshold
        assert len(bus.dead_subscribers) == 0

    def test_dead_subscribers_property_empty(self):
        bus = EnhancedBus()
        assert bus.dead_subscribers == []

    def test_unsubscribe_clears_dead_status(self):
        bus = EnhancedBus()
        bus.subscribe("stack.push", self._bad_callback)
        for _ in range(3):
            bus.publish(create_event(EventType.STACK_PUSH, "test"))
        assert len(bus.dead_subscribers) == 1
        bus.unsubscribe("stack.push", self._bad_callback)
        assert len(bus.dead_subscribers) == 0


# ===========================================================================
# T064 — Event history
# ===========================================================================


class TestEventHistory:
    def test_history_records_events(self):
        bus = EnhancedBus()
        bus.publish(create_event(EventType.STACK_PUSH, "a"))
        bus.publish(create_event(EventType.STACK_POP, "b"))
        assert len(bus.history) == 2

    def test_history_bounded(self):
        bus = EnhancedBus(max_history=5)
        for i in range(10):
            bus.publish(create_event(EventType.CUSTOM, f"src-{i}"))
        assert len(bus.history) == 5
        assert bus.history[0].source == "src-5"

    def test_clear_history(self):
        bus = EnhancedBus()
        bus.publish(create_event(EventType.CUSTOM, "x"))
        bus.clear_history()
        assert bus.history == []

    def test_history_default_limit(self):
        bus = EnhancedBus()
        assert bus._max_history == 100

    def test_history_empty_bus(self):
        bus = EnhancedBus()
        assert bus.history == []


# ===========================================================================
# T063 — bus_handler API functions
# ===========================================================================


class TestBusHandler:
    def _fresh_bus(self):
        bus = EnhancedBus()
        set_bus(bus)
        return bus

    def test_handle_publish(self):
        self._fresh_bus()
        result = handle_publish("stack.push", "cli", {"direction": "up"})
        assert result["status"] == "ok"
        assert result["event_type"] == "stack.push"
        assert result["delivered"] == 0  # no subscribers yet

    def test_handle_subscribe(self):
        self._fresh_bus()
        result = handle_subscribe("stack.*")
        assert result["status"] == "subscribed"
        assert result["pattern"] == "stack.*"
        assert result["subscriber_count"] == 1

    def test_handle_list_subscribers(self):
        self._fresh_bus()
        handle_subscribe("stack.*")
        handle_subscribe("pane.*")
        result = handle_list_subscribers()
        assert result["status"] == "ok"
        assert result["total"] == 2
        assert "stack.*" in result["patterns"]

    def test_handle_history(self):
        self._fresh_bus()
        handle_publish("stack.push", "test", {})
        handle_publish("pane.kill", "test", {})
        result = handle_history(limit=10)
        assert result["status"] == "ok"
        assert result["count"] == 2
        assert result["events"][0]["event_type"] == "stack.push"

    def test_handle_history_limit(self):
        self._fresh_bus()
        for _ in range(5):
            handle_publish("custom", "test", {})
        result = handle_history(limit=3)
        assert result["count"] == 3

    def test_handle_publish_unknown_type_falls_back_to_custom(self):
        self._fresh_bus()
        result = handle_publish("unknown.event", "test", {})
        assert result["status"] == "ok"
