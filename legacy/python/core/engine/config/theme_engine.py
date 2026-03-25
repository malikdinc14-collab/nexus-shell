"""Theme engine — reads theme YAML and generates tmux color commands."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover – fallback for minimal envs
    yaml = None  # type: ignore


@dataclass
class Theme:
    name: str
    colors: Dict[str, str] = field(default_factory=dict)
    # Expected keys: bg, fg, accent, border, active_border,
    #                message_bg, message_fg, status_bg, status_fg


def load_theme(path: str) -> Optional[Theme]:
    """Load a theme from a YAML file. Returns None on error."""
    if yaml is None:
        return None
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    return Theme(
        name=data.get("name", os.path.splitext(os.path.basename(path))[0]),
        colors=data.get("colors", {}),
    )


def generate_tmux_commands(theme: Theme) -> List[str]:
    """Convert theme colors to a list of tmux ``set`` command strings."""
    c = theme.colors
    commands: List[str] = []

    status_bg = c.get("status_bg") or c.get("bg", "default")
    status_fg = c.get("status_fg") or c.get("fg", "default")
    border_fg = c.get("border") or c.get("fg", "default")
    active_border_fg = c.get("active_border") or c.get("accent", "default")
    message_bg = c.get("message_bg") or c.get("bg", "default")
    message_fg = c.get("message_fg") or c.get("accent", "default")

    commands.append(f'set -g status-bg "{status_bg}"')
    commands.append(f'set -g status-fg "{status_fg}"')
    commands.append(f'set -g pane-border-style "fg={border_fg}"')
    commands.append(f'set -g pane-active-border-style "fg={active_border_fg}"')
    commands.append(f'set -g message-style "bg={message_bg},fg={message_fg}"')

    return commands


def handle_apply_theme(name: str, config_dirs: List[str]) -> dict:
    """Search *config_dirs* for a theme and return tmux commands.

    Looks for ``theme.yaml`` or ``themes/{name}.yaml`` in each directory.
    """
    for d in config_dirs:
        candidates = [
            os.path.join(d, "theme.yaml"),
            os.path.join(d, "themes", f"{name}.yaml"),
        ]
        for path in candidates:
            theme = load_theme(path)
            if theme is not None:
                return {
                    "action": "apply_theme",
                    "name": name,
                    "commands": generate_tmux_commands(theme),
                }
    return {"error": "theme_not_found", "name": name}
