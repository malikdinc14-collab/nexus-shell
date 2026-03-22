#!/usr/bin/env python3
# core/engine/capabilities/adapters/menu/null_menu.py
"""
NullMenuAdapter -- Stdin Fallback for MenuCapability
=====================================================
Always-available fallback that uses simple numbered stdin selection.
Registered at priority 0 so it is only used when no real menu tool
(fzf, gum, textual) is present.
"""

from typing import List, Optional
from ...base import MenuCapability, AdapterManifest, CapabilityType


class NullMenuAdapter(MenuCapability):
    """
    Minimal menu adapter that prints numbered options and reads
    a selection from stdin. Works in any terminal, no dependencies.
    """

    manifest = AdapterManifest(
        name="null-menu",
        capability_type=CapabilityType.MENU,
        priority=0,
        binary="true",  # /usr/bin/true — always available
    )

    @property
    def capability_type(self):
        return CapabilityType.MENU

    @property
    def capability_id(self):
        return "null-menu"

    def is_available(self) -> bool:
        return True

    def show_menu(self, options: List[str], prompt: str = "Select:") -> Optional[str]:
        if not options:
            return None
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
        try:
            choice = input(f"{prompt}> ")
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except (ValueError, IndexError, EOFError):
            pass
        return None

    def pick(self, context: str, items_json: List[str]) -> Optional[str]:
        return self.show_menu(items_json, context)
