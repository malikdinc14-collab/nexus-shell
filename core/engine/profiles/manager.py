"""Profile manager for nexus-shell.

Loads profile YAML files and manages the active profile.
Profiles are orthogonal to packs — switching profiles never touches packs.
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class Profile:
    """A nexus-shell profile definition."""

    name: str
    description: str = ""
    composition: Optional[str] = None
    theme: Optional[str] = None
    hud: Dict[str, Any] = field(default_factory=dict)
    keybind_overrides: Dict[str, str] = field(default_factory=dict)
    menu_nodes: List[Dict[str, Any]] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)


def load_profile(path: str) -> Optional[Profile]:
    """Read a profile YAML file and return a Profile, or None on error."""
    try:
        with open(path, "r") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict) or "name" not in data:
            return None
        return Profile(
            name=data["name"],
            description=data.get("description", ""),
            composition=data.get("composition"),
            theme=data.get("theme"),
            hud=data.get("hud", {}),
            keybind_overrides=data.get("keybind_overrides", {}),
            menu_nodes=data.get("menu_nodes", []),
            env=data.get("env", {}),
        )
    except (OSError, yaml.YAMLError, TypeError):
        return None


class ProfileManager:
    """Manages loading, listing, and switching profiles."""

    def __init__(self, profiles_dir: str) -> None:
        self._profiles: Dict[str, Profile] = {}
        self._active: Optional[Profile] = None
        self._scan(profiles_dir)

    # -- internal -----------------------------------------------------------

    def _scan(self, profiles_dir: str) -> None:
        if not os.path.isdir(profiles_dir):
            return
        for path in sorted(glob.glob(os.path.join(profiles_dir, "*.yaml"))):
            prof = load_profile(path)
            if prof is not None:
                self._profiles[prof.name] = prof

    # -- public API ---------------------------------------------------------

    @property
    def available_profiles(self) -> List[Profile]:
        """Return all loaded profiles."""
        return list(self._profiles.values())

    @property
    def active_profile(self) -> Optional[Profile]:
        """Return the currently active profile, or None."""
        return self._active

    def switch(self, name: str) -> bool:
        """Switch to the named profile. Returns True if found."""
        prof = self._profiles.get(name)
        if prof is None:
            return False
        self._active = prof
        return True

    def get(self, name: str) -> Optional[Profile]:
        """Return a profile by name, or None."""
        return self._profiles.get(name)

    def list_names(self) -> List[str]:
        """Return the names of all available profiles."""
        return list(self._profiles.keys())
