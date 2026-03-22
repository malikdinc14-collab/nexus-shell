"""Tab and TabStack data models for nexus-shell tab management."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from uuid import uuid4


@dataclass
class Tab:
    """A single logical tab within a TabStack.

    A Tab represents one running tool (editor, terminal, chat, menu, etc.)
    that can be attached to a tmux pane or shelved in the reservoir.
    """

    capability_type: str  # "editor", "terminal", "chat", "menu", etc.
    adapter_name: str  # "neovim", "zsh", "opencode", "fzf", etc.
    id: str = field(default_factory=lambda: str(uuid4()))
    tmux_pane_id: Optional[str] = None  # Physical tmux pane (None if in reservoir)
    command: str = ""  # Launch command
    cwd: str = ""  # Working directory
    role: Optional[str] = None  # User-assigned role tag
    env: Dict[str, str] = field(default_factory=dict)
    is_active: bool = False  # Currently visible in the stack
    native_multiplicity: bool = False  # Adapter handles its own tabs


@dataclass
class TabStack:
    """An ordered collection of Tabs assigned to one tmux pane.

    Only one Tab is active (visible) at a time. Push, pop, and rotate
    operations switch between tabs atomically.
    """

    pane_id: str  # tmux pane identifier
    id: str = field(default_factory=lambda: str(uuid4()))
    tabs: List[Tab] = field(default_factory=list)
    active_index: int = 0
    role: Optional[str] = None  # User-assigned stack identity

    @property
    def active_tab(self) -> Optional[Tab]:
        """Return the currently active Tab, or None if the stack is empty."""
        if not self.tabs:
            return None
        return self.tabs[self.active_index]

    def push(self, tab: Tab) -> None:
        """Push a tab onto the stack and make it active.

        Deactivates the current active tab (if any), attaches the new tab
        to this stack's pane, and sets it as active.
        """
        # Deactivate current active tab
        if self.tabs:
            self.tabs[self.active_index].is_active = False

        # Attach and activate the new tab
        tab.tmux_pane_id = self.pane_id
        tab.is_active = True
        self.tabs.append(tab)
        self.active_index = len(self.tabs) - 1

    def pop(self) -> Optional[Tab]:
        """Remove and return the active tab. Activates the next tab.

        Returns None if the stack is empty. The popped tab is detached
        (tmux_pane_id set to None, is_active set to False).
        """
        if not self.tabs:
            return None

        # Remove the active tab
        tab = self.tabs.pop(self.active_index)
        tab.is_active = False
        tab.tmux_pane_id = None

        # Fix active_index and activate the next tab
        if self.tabs:
            self.active_index = min(self.active_index, len(self.tabs) - 1)
            self.tabs[self.active_index].is_active = True
        else:
            self.active_index = 0

        return tab

    def rotate(self, direction: int) -> None:
        """Rotate the active tab by direction (+1 forward, -1 backward).

        Wraps around at boundaries. No-op if stack has 0 or 1 tabs.
        """
        if len(self.tabs) <= 1:
            return

        self.tabs[self.active_index].is_active = False
        self.active_index = (self.active_index + direction) % len(self.tabs)
        self.tabs[self.active_index].is_active = True
