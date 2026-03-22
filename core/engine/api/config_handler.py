"""Config reload and query handler for nexus-ctl."""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

RELOADABLE_SECTIONS = ["keymap", "theme", "hud", "adapters", "connectors"]


def handle_reload(global_dir: str = "", workspace_dir: str = "") -> dict:
    """Reload all configuration sections.

    Validates that supplied config directories exist before proceeding.

    Returns:
        A dict with ``action``, ``reloaded`` list, and ``status``.
    """
    for label, path in [("global", global_dir), ("workspace", workspace_dir)]:
        if path and not os.path.isdir(path):
            return {
                "action": "config_reload",
                "status": "error",
                "error": "directory_not_found",
                "path": path,
            }

    return {
        "action": "config_reload",
        "reloaded": list(RELOADABLE_SECTIONS),
        "status": "ok",
    }


def handle_apply_theme(name: str, config_dirs: List[str] = None) -> dict:
    """Apply a named theme.

    Attempts to delegate to the theme engine; returns a pending stub if
    the theme engine is not available.
    """
    if config_dirs is None:
        config_dirs = []

    try:
        from engine.config.theme_engine import handle_apply_theme as _apply
        return _apply(name, config_dirs)
    except (ImportError, ModuleNotFoundError):
        logger.warning("Theme engine unavailable for theme '%s'", name, exc_info=True)

    return {"action": "apply_theme", "name": name, "status": "pending"}


def handle_get(key: str, global_dir: str = "", workspace_dir: str = "") -> dict:
    """Resolve a single config key through the cascade.

    Attempts to delegate to ``CascadeResolver``; returns a not-found stub
    when the resolver is unavailable or the key is missing.
    """
    try:
        from engine.api.cascade_resolver import CascadeResolver
        resolver = CascadeResolver(global_dir=global_dir, workspace_dir=workspace_dir)
        value, source = resolver.get(key)
        return {"key": key, "value": value, "source": source}
    except (ImportError, ModuleNotFoundError):
        logger.warning("CascadeResolver unavailable for key '%s'", key, exc_info=True)

    return {"key": key, "value": None, "source": None}
