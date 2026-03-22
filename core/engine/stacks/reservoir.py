"""TabReservoir — holds detached tabs not currently assigned to any pane."""

from dataclasses import dataclass, field
from typing import Optional, List

from engine.stacks.stack import Tab


@dataclass
class TabReservoir:
    """A holding area for tabs that have been detached from their stacks.

    Tabs in the reservoir have no tmux pane assignment and are inactive.
    They can be recalled into any target pane on demand.
    """

    tabs: List[Tab] = field(default_factory=list)

    def shelve(self, tab: Tab) -> None:
        """Detach a tab from its pane and add it to the reservoir.

        Sets tmux_pane_id to None and is_active to False.
        """
        tab.tmux_pane_id = None
        tab.is_active = False
        self.tabs.append(tab)

    def recall(self, tab_id: str, target_pane_id: str) -> Optional[Tab]:
        """Pull a tab from the reservoir and assign it to a pane.

        Returns the tab if found, None otherwise.
        """
        for i, tab in enumerate(self.tabs):
            if tab.id == tab_id:
                self.tabs.pop(i)
                tab.tmux_pane_id = target_pane_id
                return tab
        return None
