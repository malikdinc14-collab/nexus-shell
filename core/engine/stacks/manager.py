"""StackManager — runtime manager that tracks all TabStacks across all panes."""

import uuid
from typing import Dict, List, Optional, Tuple, Callable

from engine.stacks.stack import Tab, TabStack
from engine.stacks.reservoir import TabReservoir


class LastTabWarning:
    """Sentinel returned when pop() would remove the last tab."""
    pass


class NativelyManaged:
    """Sentinel returned when operation is delegated to the adapter's native tab system."""
    pass


class StackManager:
    """Maps stack IDs to TabStack instances and manages tab operations.

    Supports identity-based lookup (role, tag, UUID) matching the daemon's
    resolution semantics.
    """

    def __init__(self) -> None:
        self._stacks: Dict[str, TabStack] = {}
        self.reservoir: TabReservoir = TabReservoir()
        self.events: List[str] = []

    # -- Identity resolution ---------------------------------------------------

    def get_by_identity(self, identity: str) -> Tuple[Optional[str], Optional[TabStack]]:
        """Resolve a stack by UUID, role, or tag. Returns (sid, stack) or (None, None)."""
        # Direct UUID match
        if identity in self._stacks:
            return identity, self._stacks[identity]
        # Role match
        for sid, stack in self._stacks.items():
            if stack.role == identity:
                return sid, stack
        # Tag match
        for sid, stack in self._stacks.items():
            if identity in stack.tags:
                return sid, stack
        return None, None

    def get_or_create(self, pane_id: str) -> TabStack:
        """Return the existing stack for pane_id, or create a new anonymous one."""
        if pane_id not in self._stacks:
            self._stacks[pane_id] = TabStack(pane_id=pane_id)
        return self._stacks[pane_id]

    def get_or_create_by_identity(
        self, identity: str, initial_pane: Optional[str] = None
    ) -> Tuple[str, TabStack]:
        """Resolve or create a stack by identity (role/UUID/tag).

        Matches daemon's _get_or_create_stack semantics.
        """
        # Direct UUID lookup
        if identity and identity.startswith("stack_"):
            if identity in self._stacks:
                return identity, self._stacks[identity]

        # Role/tag lookup
        if identity and not identity.startswith("stack_"):
            sid, stack = self.get_by_identity(identity)
            if sid:
                return sid, stack

        # Create new
        is_uuid = identity and identity.startswith("stack_")
        sid = identity if is_uuid else f"stack_{uuid.uuid4().hex[:6]}"
        role = None if is_uuid else identity

        stack = TabStack(pane_id=sid, id=sid, role=role)
        if initial_pane:
            tab = Tab(
                tmux_pane_id=initial_pane,
                name=role.capitalize() if role else "Shell",
                status="VISIBLE",
                is_active=True,
            )
            stack.tabs.append(tab)

        self._stacks[sid] = stack
        return sid, stack

    def get_stack(self, pane_id: str) -> Optional[TabStack]:
        """Return the TabStack for pane_id, or None if not tracked."""
        return self._stacks.get(pane_id)

    # -- Operations ------------------------------------------------------------

    def push(self, pane_id: str, tab: Tab):
        """Push a tab onto the pane's stack."""
        stack = self.get_or_create(pane_id)
        if stack.active_tab and stack.active_tab.native_multiplicity:
            return NativelyManaged()
        stack.push(tab)
        self.events.append("tab.pushed")
        return None

    def pop(self, pane_id: str):
        """Pop the active tab from the pane's stack."""
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
        """Rotate through tabs in the pane's stack."""
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
        """Remove a pane's stack entirely."""
        self._stacks.pop(pane_id, None)

    def all_stacks(self) -> Dict[str, TabStack]:
        """Return all tracked stacks."""
        return dict(self._stacks)

    # -- Scrubbing -------------------------------------------------------------

    def scrub(self, container_exists: Callable[[str], bool]) -> List[str]:
        """Remove stacks with dead panes. Returns list of removed stack IDs."""
        dead = []
        for sid, stack in list(self._stacks.items()):
            live_tabs = [
                t for t in stack.tabs
                if t.tmux_pane_id and container_exists(t.tmux_pane_id)
            ]
            if not live_tabs:
                dead.append(sid)
            elif len(live_tabs) != len(stack.tabs):
                stack.tabs = live_tabs
                stack.active_index = min(stack.active_index, len(live_tabs) - 1)
        for sid in dead:
            del self._stacks[sid]
        return dead

    # -- Serialization ---------------------------------------------------------

    def serialize(self) -> dict:
        """Serialize all stacks to daemon-compatible JSON format."""
        return {
            "stacks": {
                sid: stack.to_dict()
                for sid, stack in self._stacks.items()
            }
        }

    def deserialize(self, data: dict) -> None:
        """Load stacks from daemon JSON format."""
        self._stacks.clear()
        for sid, stack_data in data.get("stacks", {}).items():
            self._stacks[sid] = TabStack.from_dict(sid, stack_data)
