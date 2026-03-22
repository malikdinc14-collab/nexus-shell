"""Enhanced event bus with wildcard subscriptions, dead subscriber detection, and history."""

from __future__ import annotations

import fnmatch
import logging
from collections import defaultdict, deque
from typing import Callable, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)

from engine.bus.typed_events import TypedEvent


class EnhancedBus:
    """Event bus supporting wildcard patterns and dead subscriber detection.

    Patterns use fnmatch-style wildcards:
      - ``stack.*`` matches ``stack.push``, ``stack.pop``, etc.
      - ``*.push`` matches ``stack.push``, ``queue.push``, etc.
      - ``*.*`` matches any dotted event type
    """

    _DEAD_THRESHOLD = 3  # consecutive failures before marking dead

    def __init__(self, max_history: int = 100) -> None:
        # pattern -> set of callbacks
        self._subscribers: Dict[str, Set[Callable]] = defaultdict(set)
        # callback -> consecutive failure count
        self._failure_counts: Dict[Tuple[str, Callable], int] = defaultdict(int)
        # set of (pattern, callback) pairs marked dead
        self._dead: Set[Tuple[str, Callable]] = set()
        # bounded event history
        self._history: deque = deque(maxlen=max_history)
        self._max_history = max_history

    # ------------------------------------------------------------------
    # Subscribe / unsubscribe
    # ------------------------------------------------------------------

    def subscribe(self, pattern: str, callback: Callable) -> None:
        """Register *callback* to receive events matching *pattern*."""
        self._subscribers[pattern].add(callback)

    def unsubscribe(self, pattern: str, callback: Callable) -> None:
        """Remove a previously registered subscription."""
        if pattern in self._subscribers:
            self._subscribers[pattern].discard(callback)
            if not self._subscribers[pattern]:
                del self._subscribers[pattern]
        # Clean up bookkeeping
        key = (pattern, callback)
        self._failure_counts.pop(key, None)
        self._dead.discard(key)

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish(self, event: TypedEvent) -> int:
        """Deliver *event* to all matching subscribers. Returns delivery count."""
        self._history.append(event)
        event_name = event.event_type.value
        delivered = 0

        for pattern, callbacks in list(self._subscribers.items()):
            if not self._match_pattern(pattern, event_name):
                continue
            for cb in list(callbacks):
                key = (pattern, cb)
                if key in self._dead:
                    continue
                try:
                    cb(event)
                    # Reset failure count on success
                    self._failure_counts.pop(key, None)
                    delivered += 1
                except Exception:
                    self._failure_counts[key] += 1
                    if self._failure_counts[key] >= self._DEAD_THRESHOLD:
                        self._dead.add(key)
                        logger.warning(
                            "Subscriber marked dead after %d failures: pattern='%s' callback=%r",
                            self._DEAD_THRESHOLD, pattern, cb,
                        )
        return delivered

    # ------------------------------------------------------------------
    # Pattern matching
    # ------------------------------------------------------------------

    @staticmethod
    def _match_pattern(pattern: str, event_type: str) -> bool:
        """Return True if *pattern* matches *event_type* using fnmatch rules."""
        return fnmatch.fnmatch(event_type, pattern)

    # ------------------------------------------------------------------
    # Dead subscriber introspection
    # ------------------------------------------------------------------

    def _detect_dead_subscribers(self) -> List[Tuple[str, Callable]]:
        """Return list of (pattern, callback) pairs marked as dead."""
        return list(self._dead)

    @property
    def dead_subscribers(self) -> List[Tuple[str, Callable]]:
        """Return dead subscriber entries."""
        return self._detect_dead_subscribers()

    # ------------------------------------------------------------------
    # Subscriber count
    # ------------------------------------------------------------------

    @property
    def subscriber_count(self) -> int:
        """Total number of active (non-dead) subscriptions."""
        total = 0
        for pattern, callbacks in self._subscribers.items():
            for cb in callbacks:
                if (pattern, cb) not in self._dead:
                    total += 1
        return total

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    @property
    def history(self) -> List[TypedEvent]:
        """Return list of recent events (most recent last)."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear the event history."""
        self._history.clear()
