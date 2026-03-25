"""Workspace handler for composition switching, save, and restore.

Supports:
  nexus-ctl workspace switch-composition <name>
  nexus-ctl workspace save
  nexus-ctl workspace restore [name]
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

from engine.compositions.schema import (
    load_composition,
    list_composition_names,
    load_compositions_from_directory,
)
from engine.momentum.session import save_session, restore_session, load_geometry
from engine.api.runtime import get_manager

# Module-level composition directory
COMPOSITIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "ui", "compositions"
)
COMPOSITIONS_DIR = os.path.normpath(COMPOSITIONS_DIR)


def _get_session_dir(name: str = "") -> str:
    """Resolve the session directory from env, name, or tmux session."""
    env_dir = os.environ.get("NEXUS_SESSION_DIR")
    if env_dir:
        return env_dir
    if name:
        base = os.path.expanduser("~/.local/share/nexus/sessions")
        return os.path.join(base, name)
    try:
        tmux_name = subprocess.check_output(
            ["tmux", "display-message", "-p", "#S"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        ).decode().strip()
    except Exception:
        logger.warning("Failed to get tmux session name, using 'default'", exc_info=True)
        tmux_name = "default"
    base = os.path.expanduser("~/.local/share/nexus/sessions")
    return os.path.join(base, tmux_name)


def handle_save() -> Dict[str, Any]:
    """Save the current workspace via the momentum session module."""
    try:
        manager = get_manager()
        session_dir = _get_session_dir()
        save_session(manager, session_dir)
        return {"action": "save_workspace", "status": "saved", "session_dir": session_dir}
    except Exception as exc:
        return {"action": "save_workspace", "status": "error", "error": str(exc)}


def handle_restore(name: str = "") -> Dict[str, Any]:
    """Restore a workspace via the momentum session module."""
    try:
        manager = get_manager()
        session_dir = _get_session_dir(name)
        deferred = restore_session(manager, session_dir)
        load_geometry(session_dir)
        return {
            "action": "restore_workspace",
            "status": "restored",
            "session_dir": session_dir,
            "deferred_count": len(deferred._pending),
        }
    except Exception as exc:
        return {"action": "restore_workspace", "status": "error", "error": str(exc)}


def handle_switch_composition(name: str) -> Dict[str, Any]:
    """Look up a composition by name and return switch instructions.

    Returns pane count and description on success, or an error dict with
    the list of available compositions when the name is not found.
    """
    json_path = os.path.join(COMPOSITIONS_DIR, f"{name}.json")
    comp = load_composition(json_path)

    if comp is not None:
        return {
            "action": "switch_composition",
            "name": name,
            "panes": len(comp.panes),
            "description": comp.description,
        }

    available = list_composition_names(COMPOSITIONS_DIR)
    return {
        "error": "composition_not_found",
        "name": name,
        "available": available,
    }
