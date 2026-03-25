"""Shared runtime singletons for nexus-shell API handlers.

All handlers that operate on tab stacks must share the same StackManager
instance. This module provides the single source of truth.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

from engine.stacks.manager import StackManager

_manager: Optional[StackManager] = None


def get_manager() -> StackManager:
    """Return the shared StackManager, creating one if needed."""
    global _manager
    if _manager is None:
        _manager = StackManager()
    return _manager


def set_manager(manager: StackManager) -> None:
    """Replace the shared StackManager (for testing or re-init)."""
    global _manager
    _manager = manager


def reset() -> None:
    """Reset all shared state. Intended for tests only."""
    global _manager
    _manager = None
