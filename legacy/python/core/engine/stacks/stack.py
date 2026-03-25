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

    capability_type: str = "terminal"
    adapter_name: str = "zsh"
    id: str = field(default_factory=lambda: str(uuid4()))
    tmux_pane_id: Optional[str] = None  # Physical pane (None if in reservoir)
    command: str = ""
    cwd: str = ""
    role: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    is_active: bool = False
    native_multiplicity: bool = False
    name: str = "Shell"  # Display name
    status: str = "BACKGROUND"  # VISIBLE or BACKGROUND
    geometry: Optional[Dict] = None  # {x, y, w, h} snapshot for restore


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
    role: Optional[str] = None  # Semantic identity (e.g. "editor", "terminal")
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def active_tab(self) -> Optional[Tab]:
        """Return the currently active Tab, or None if the stack is empty."""
        if not self.tabs:
            return None
        if self.active_index >= len(self.tabs):
            self.active_index = len(self.tabs) - 1
        return self.tabs[self.active_index]

    def push(self, tab: Tab) -> None:
        """Push a tab onto the stack and make it active."""
        if self.tabs:
            self.tabs[self.active_index].is_active = False
            self.tabs[self.active_index].status = "BACKGROUND"

        tab.tmux_pane_id = self.pane_id
        tab.is_active = True
        tab.status = "VISIBLE"
        self.tabs.append(tab)
        self.active_index = len(self.tabs) - 1

    def pop(self) -> Optional[Tab]:
        """Remove and return the active tab. Activates the next tab."""
        if not self.tabs:
            return None

        tab = self.tabs.pop(self.active_index)
        tab.is_active = False
        tab.status = "BACKGROUND"
        tab.tmux_pane_id = None

        if self.tabs:
            self.active_index = min(self.active_index, len(self.tabs) - 1)
            self.tabs[self.active_index].is_active = True
            self.tabs[self.active_index].status = "VISIBLE"
        else:
            self.active_index = 0

        return tab

    def rotate(self, direction: int) -> None:
        """Rotate the active tab by direction (+1 forward, -1 backward)."""
        if len(self.tabs) <= 1:
            return

        self.tabs[self.active_index].is_active = False
        self.tabs[self.active_index].status = "BACKGROUND"
        self.active_index = (self.active_index + direction) % len(self.tabs)
        self.tabs[self.active_index].is_active = True
        self.tabs[self.active_index].status = "VISIBLE"

    def to_dict(self) -> dict:
        """Serialize to daemon-compatible JSON format."""
        return {
            "role": self.role,
            "tags": list(self.tags),
            "active_index": self.active_index,
            "tabs": [
                {
                    "id": t.tmux_pane_id or t.id,
                    "name": t.name,
                    "status": t.status,
                    "geometry": t.geometry,
                }
                for t in self.tabs
            ],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, sid: str, data: dict) -> "TabStack":
        """Deserialize from daemon JSON format."""
        tabs = []
        for t in data.get("tabs", []):
            tabs.append(Tab(
                tmux_pane_id=t.get("id"),
                name=t.get("name", "Shell"),
                status=t.get("status", "BACKGROUND"),
                geometry=t.get("geometry"),
                is_active=(t.get("status") == "VISIBLE"),
            ))
        return cls(
            pane_id=sid,
            id=sid,
            tabs=tabs,
            active_index=data.get("active_index", 0),
            role=data.get("role"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
