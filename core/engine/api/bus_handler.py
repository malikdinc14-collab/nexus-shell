"""CLI/API handler functions for the Nexus event bus."""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

from engine.bus.typed_events import EventType, TypedEvent, create_event
from engine.bus.enhanced_bus import EnhancedBus

# Module-level singleton bus (can be replaced in tests or by the runtime).
_bus: Optional[EnhancedBus] = None


def get_bus() -> EnhancedBus:
    """Return the module-level EnhancedBus, creating one if needed."""
    global _bus
    if _bus is None:
        _bus = EnhancedBus()
    return _bus


def set_bus(bus: EnhancedBus) -> None:
    """Replace the module-level bus (useful for tests)."""
    global _bus
    _bus = bus


def _resolve_event_type(name: str) -> EventType:
    """Map a dotted string like 'stack.push' to the EventType enum value.

    Falls back to CUSTOM if the name is not recognised.
    """
    for et in EventType:
        if et.value == name:
            return et
    return EventType.CUSTOM


def handle_publish(event_type: str, source: str, payload: dict) -> dict:
    """Publish an event via the shared bus. Returns delivery summary."""
    bus = get_bus()
    et = _resolve_event_type(event_type)
    event = create_event(et, source, **payload)
    count = bus.publish(event)
    return {
        "status": "ok",
        "event_type": event_type,
        "delivered": count,
    }


def handle_subscribe(pattern: str) -> dict:
    """Register a subscription (placeholder callback). Returns confirmation."""
    bus = get_bus()
    # For CLI usage we store a no-op; real runtime replaces this.
    bus.subscribe(pattern, lambda e: None)
    return {
        "status": "subscribed",
        "pattern": pattern,
        "subscriber_count": bus.subscriber_count,
    }


def handle_list_subscribers() -> dict:
    """Return current subscriber patterns and counts."""
    bus = get_bus()
    patterns: Dict[str, int] = {}
    for pattern, callbacks in bus._subscribers.items():
        active = sum(
            1 for cb in callbacks if (pattern, cb) not in bus._dead
        )
        if active:
            patterns[pattern] = active
    return {
        "status": "ok",
        "patterns": patterns,
        "total": bus.subscriber_count,
    }


def handle_history(limit: int = 20) -> dict:
    """Return the last *limit* events from history."""
    bus = get_bus()
    events = bus.history[-limit:] if limit < len(bus.history) else bus.history
    serialised = [
        {
            "event_type": e.event_type.value,
            "source": e.source,
            "payload": e.payload,
            "timestamp": e.timestamp,
        }
        for e in events
    ]
    return {
        "status": "ok",
        "events": serialised,
        "count": len(serialised),
    }
