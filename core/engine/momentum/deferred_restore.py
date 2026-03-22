"""Deferred tab restoration — queues tabs until panes become available."""

from typing import Dict, List

from engine.stacks.stack import Tab


class DeferredRestore:
    """Queues tab restoration until target panes are available.

    After a session restore, the physical tmux panes may not exist yet.
    ``DeferredRestore`` holds the pending tabs keyed by their original
    pane id so they can be applied once the pane is created.
    """

    def __init__(self) -> None:
        self._pending: Dict[str, List[Tab]] = {}

    def queue_restore(self, pane_id: str, tabs: List[Tab]) -> None:
        """Store *tabs* as pending for *pane_id*."""
        if tabs:
            self._pending.setdefault(pane_id, []).extend(tabs)

    def apply_pending(self, pane_id: str) -> List[Tab]:
        """Return and clear pending tabs for *pane_id*.

        Returns an empty list if nothing is pending.
        """
        return self._pending.pop(pane_id, [])

    def pending_count(self) -> int:
        """Total number of tabs waiting across all panes."""
        return sum(len(v) for v in self._pending.values())

    def pending_panes(self) -> List[str]:
        """Return list of pane ids that have pending restores."""
        return list(self._pending.keys())
