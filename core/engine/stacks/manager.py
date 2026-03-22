"""StackManager — runtime manager that tracks all TabStacks across all panes."""

from typing import Dict, List, Optional

from engine.stacks.stack import Tab, TabStack
from engine.stacks.reservoir import TabReservoir


class LastTabWarning:
    """Sentinel returned when pop() would remove the last tab."""
    pass


class NativelyManaged:
    """Sentinel returned when operation is delegated to the adapter's native tab system."""
    pass


class StackManager:
    """Maps tmux pane IDs to TabStack instances and manages tab operations.

    Tracks all TabStacks across all panes, handles native multiplicity
    delegation, and records events for later bus integration.
    """

    def __init__(self) -> None:
        self._stacks: Dict[str, TabStack] = {}
        self.reservoir: TabReservoir = TabReservoir()
        self.events: List[str] = []

    def get_or_create(self, pane_id: str) -> TabStack:
        """Return the existing stack for pane_id, or create a new anonymous one."""
        if pane_id not in self._stacks:
            self._stacks[pane_id] = TabStack(pane_id=pane_id)
        return self._stacks[pane_id]

    def get_stack(self, pane_id: str) -> Optional[TabStack]:
        """Return the TabStack for pane_id, or None if not tracked."""
        return self._stacks.get(pane_id)

    def push(self, pane_id: str, tab: Tab):
        """Push a tab onto the pane's stack.

        If the active tab has native_multiplicity=True, returns NativelyManaged
        sentinel instead of operating on the stack.
        """
        stack = self.get_or_create(pane_id)
        if stack.active_tab and stack.active_tab.native_multiplicity:
            return NativelyManaged()
        stack.push(tab)
        self.events.append("tab.pushed")
        return None

    def pop(self, pane_id: str):
        """Pop the active tab from the pane's stack.

        Returns:
            - NativelyManaged sentinel if active tab has native_multiplicity
            - LastTabWarning sentinel if this is the last tab
            - The popped Tab on success
            - None if stack is empty or pane not tracked
        """
        stack = self.get_stack(pane_id)
        if stack is None:
            return None
        if not stack.tabs:
            return None
        if stack.active_tab and stack.active_tab.native_multiplicity:
            return NativelyManaged()
        if len(stack.tabs) == 1:
            return LastTabWarning()
        tab = stack.pop()
        self.events.append("tab.popped")
        return tab

    def rotate(self, pane_id: str, direction: int):
        """Rotate through tabs in the pane's stack.

        Returns:
            - NativelyManaged sentinel if active tab has native_multiplicity
            - The new active Tab after rotation
            - None if stack doesn't exist or has <= 1 tab
        """
        stack = self.get_stack(pane_id)
        if stack is None:
            return None
        if stack.active_tab and stack.active_tab.native_multiplicity:
            return NativelyManaged()
        if len(stack.tabs) <= 1:
            return None
        stack.rotate(direction)
        self.events.append("tab.rotated")
        return stack.active_tab

    def remove_stack(self, pane_id: str) -> None:
        """Remove a pane's stack entirely (e.g. on pane kill)."""
        self._stacks.pop(pane_id, None)

    def all_stacks(self) -> Dict[str, TabStack]:
        """Return all tracked stacks."""
        return dict(self._stacks)
