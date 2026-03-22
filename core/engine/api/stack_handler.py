"""Stack handler — bridge between the CLI and the StackManager.

Handles `nexus-ctl stack {push|pop|rotate}` commands as pure Python
data-model operations. No tmux subprocess calls.
"""

import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

from engine.stacks.stack import Tab
from engine.stacks.manager import LastTabWarning, NativelyManaged
from engine.api.runtime import get_manager


def handle_push(
    pane_id: str,
    capability_type: str = "terminal",
    adapter_name: str = "zsh",
    command: str = "",
    cwd: str = "",
) -> Tab:
    """Create a Tab and push it onto the pane's stack.

    Returns the newly created Tab.
    """
    mgr = get_manager()
    tab = Tab(
        capability_type=capability_type,
        adapter_name=adapter_name,
        command=command,
        cwd=cwd,
    )
    result = mgr.push(pane_id, tab)
    if isinstance(result, NativelyManaged):
        return result
    return tab


def handle_pop(pane_id: str) -> Union[Tab, Dict[str, Any]]:
    """Pop the active tab from the pane's stack.

    Returns:
        - The popped Tab on success
        - {"warning": "last_tab", "pane_id": pane_id} if last tab
        - {"delegated": True} if native multiplicity
        - None if stack empty
    """
    mgr = get_manager()
    result = mgr.pop(pane_id)
    if isinstance(result, LastTabWarning):
        return {"warning": "last_tab", "pane_id": pane_id}
    if isinstance(result, NativelyManaged):
        return {"delegated": True}
    return result


def handle_rotate(pane_id: str, direction: int) -> Optional[Tab]:
    """Rotate through tabs in the pane's stack.

    Returns the new active Tab, or None if rotation is not possible.
    """
    mgr = get_manager()
    result = mgr.rotate(pane_id, direction)
    if isinstance(result, NativelyManaged):
        return result
    return result
