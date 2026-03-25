"""Tab manager — bridge between the CLI and tab list/jump operations.

Handles `nexus-ctl tabs {list|jump}` commands.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

from engine.api.runtime import get_manager


def _tab_info(tab) -> Dict[str, Any]:
    """Convert a Tab to a serializable dict."""
    return {
        "id": tab.id,
        "type": tab.capability_type,
        "adapter": tab.adapter_name,
        "role": tab.role,
        "active": tab.is_active,
    }


def handle_list(pane_id: str) -> Dict[str, Any]:
    """List all tabs in the stack for the given pane.

    Returns a dict with tab list and active index.
    """
    mgr = get_manager()
    stack = mgr.get_stack(pane_id)

    if stack is None or not stack.tabs:
        return {"pane_id": pane_id, "tabs": [], "active_index": 0}

    return {
        "pane_id": pane_id,
        "tabs": [_tab_info(tab) for tab in stack.tabs],
        "active_index": stack.active_index,
    }


def handle_jump(pane_id: str, tab_index: int) -> Dict[str, Any]:
    """Jump to a specific tab index in the pane's stack.

    Returns the jumped-to tab info, or an error if index is out of range.
    """
    mgr = get_manager()
    stack = mgr.get_stack(pane_id)

    if stack is None or not stack.tabs:
        return {"error": "index_out_of_range", "max": -1}

    if tab_index < 0 or tab_index >= len(stack.tabs):
        return {"error": "index_out_of_range", "max": len(stack.tabs) - 1}

    # Deactivate current, activate target
    if stack.tabs:
        stack.tabs[stack.active_index].is_active = False
    stack.active_index = tab_index
    stack.tabs[stack.active_index].is_active = True

    return {
        "pane_id": pane_id,
        "jumped_to": tab_index,
        "tab": _tab_info(stack.tabs[tab_index]),
    }
