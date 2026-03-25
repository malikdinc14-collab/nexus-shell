"""Project discovery — detect and load `.nexus/` configuration directories."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

NEXUS_DIR = ".nexus"


@dataclass
class ProjectConfig:
    """Parsed project-local configuration from a `.nexus/` directory."""

    root: Path
    """The project root (parent of `.nexus/`)."""

    nexus_dir: Path
    """Absolute path to the `.nexus/` directory."""

    boot_items: List[Dict[str, Any]] = field(default_factory=list)
    """Parsed boot list entries from `boot.yaml`."""

    menu_path: Optional[Path] = None
    """Path to `menu.yaml` if it exists."""

    profile: Optional[str] = None
    """Preferred profile name from `profile.yaml`."""

    theme: Optional[str] = None
    """Preferred theme from `profile.yaml`."""

    composition: Optional[str] = None
    """Preferred composition from `profile.yaml`."""

    connectors_path: Optional[Path] = None
    """Path to `connectors.yaml` if it exists."""

    raw_profile: Dict[str, Any] = field(default_factory=dict)
    """Full parsed profile.yaml contents."""


def discover(project_root: str | Path) -> Optional[ProjectConfig]:
    """Discover and parse a `.nexus/` directory in the given project root.

    Returns None if no `.nexus/` directory exists.
    """
    root = Path(project_root).resolve()
    nexus_dir = root / NEXUS_DIR

    if not nexus_dir.is_dir():
        return None

    config = ProjectConfig(root=root, nexus_dir=nexus_dir)
    logger.info("Discovered project config at %s", nexus_dir)

    # Boot list
    boot_path = nexus_dir / "boot.yaml"
    if boot_path.is_file():
        config.boot_items = _load_boot(boot_path)

    # Menu
    menu_path = nexus_dir / "menu.yaml"
    if menu_path.is_file():
        config.menu_path = menu_path

    # Profile overrides
    profile_path = nexus_dir / "profile.yaml"
    if profile_path.is_file():
        config.raw_profile = _load_yaml_dict(profile_path)
        config.profile = config.raw_profile.get("profile")
        config.theme = config.raw_profile.get("theme")
        config.composition = config.raw_profile.get("composition")

    # Connectors
    connectors_path = nexus_dir / "connectors.yaml"
    if connectors_path.is_file():
        config.connectors_path = connectors_path

    return config


def _load_boot(path: Path) -> List[Dict[str, Any]]:
    """Parse boot.yaml into a list of boot items."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to parse boot.yaml at %s: %s", path, e)
        return []

    if not isinstance(data, list):
        logger.warning("boot.yaml at %s must be a list, got %s", path, type(data).__name__)
        return []

    items = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            logger.warning("boot.yaml item %d is not a dict, skipping", i)
            continue
        if "run" not in entry:
            logger.warning("boot.yaml item %d missing 'run' field, skipping", i)
            continue
        items.append({
            "label": entry.get("label", f"boot-{i}"),
            "run": entry["run"],
            "wait": entry.get("wait", False),
            "health": entry.get("health"),
            "env": entry.get("env", {}),
        })
    return items


def _load_yaml_dict(path: Path) -> Dict[str, Any]:
    """Safely load a YAML file as a dict. Returns empty dict on failure."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("Failed to parse %s: %s", path, e)
        return {}
