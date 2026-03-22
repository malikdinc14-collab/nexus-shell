"""
Default configuration scaffolding for nexus-shell.

Creates the directory tree and seed files for:
  - Global config   (~/.config/nexus/)
  - Workspace config (.nexus/)

Existing files are NEVER overwritten.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# Global defaults
# ---------------------------------------------------------------------------

_ADAPTERS: dict = {
    "editor": "neovim",
    "explorer": "yazi",
    "chat": "opencode",
    "menu": "fzf",
    "multiplexer": "tmux",
    "executor": "zsh",
    "renderer": "bat",
}

_HUD: dict = {
    "modules": [
        {"name": "tabs", "position": "left", "refresh_ms": 1000},
        {"name": "git", "position": "center", "refresh_ms": 5000},
        {"name": "clock", "position": "right", "refresh_ms": 60000},
    ],
    "separator": " | ",
}

_CONNECTORS: dict = {
    "connectors": [],
}

_THEME: dict = {
    "name": "nexus-cyber",
}

_KEYMAP_HEADER: str = "# nexus-shell keymap configuration\n# Add key bindings below.\n"

_GLOBAL_DIRS: list[str] = [
    "profiles",
    "packs",
    "compositions",
    "actions",
    "menus",
]

# ---------------------------------------------------------------------------
# Workspace defaults
# ---------------------------------------------------------------------------

_WORKSPACE: dict = {
    "profile": None,
    "packs": [],
    "theme": None,
    "adapters": {},
}

_WORKSPACE_DIRS: list[str] = [
    "compositions",
    "actions",
    "menus",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ensure_defaults(
    global_dir: Optional[Path] = None,
    workspace_dir: Optional[Path] = None,
) -> None:
    """Create default config directories and seed files where they don't already exist.

    Args:
        global_dir:    Path to the global config root (e.g. ~/.config/nexus).
                       Pass None to skip global scaffold.
        workspace_dir: Path to the workspace config root (e.g. .nexus/).
                       Pass None to skip workspace scaffold.
    """
    if global_dir is not None:
        _ensure_global(global_dir)
    if workspace_dir is not None:
        _ensure_workspace(workspace_dir)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _write_yaml_if_missing(path: Path, data: dict) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def _write_text_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _ensure_global(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)

    _write_yaml_if_missing(root / "adapters.yaml", _ADAPTERS)
    _write_yaml_if_missing(root / "hud.yaml", _HUD)
    _write_yaml_if_missing(root / "connectors.yaml", _CONNECTORS)
    _write_yaml_if_missing(root / "theme.yaml", _THEME)
    _write_text_if_missing(root / "keymap.conf", _KEYMAP_HEADER)

    for subdir in _GLOBAL_DIRS:
        (root / subdir).mkdir(parents=True, exist_ok=True)


def _ensure_workspace(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)

    _write_yaml_if_missing(root / "workspace.yaml", _WORKSPACE)

    for subdir in _WORKSPACE_DIRS:
        (root / subdir).mkdir(parents=True, exist_ok=True)
