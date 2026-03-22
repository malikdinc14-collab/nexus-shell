"""Pane handler — bridge between the CLI and pane operations.

Handles `nexus-ctl pane {kill|split-v|split-h}` commands.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

from engine.api.runtime import get_manager


def handle_kill(pane_id: str) -> Dict[str, Any]:
    """Kill a pane, shelving all its tabs to the reservoir first.

    Returns an action dict describing what was done.
    """
    mgr = get_manager()
    stack = mgr.get_stack(pane_id)

    if stack is None or not stack.tabs:
        return {"action": "kill_pane", "pane_id": pane_id, "tabs_shelved": 0}

    count = len(stack.tabs)
    # Shelve all tabs to the reservoir before killing
    for tab in list(stack.tabs):
        mgr.reservoir.shelve(tab)

    mgr.remove_stack(pane_id)

    return {"action": "kill_pane", "pane_id": pane_id, "tabs_shelved": count}


def handle_split(pane_id: str, direction: str) -> Dict[str, Any]:
    """Request a pane split. The actual split is done by tmux.

    Args:
        pane_id: The parent pane to split from.
        direction: "v" for vertical, "h" for horizontal.

    Returns an action dict. new_pane is "pending" because tmux
    assigns the pane ID after the split completes.
    """
    return {
        "action": "split",
        "direction": direction,
        "parent_pane": pane_id,
        "new_pane": "pending",
    }
