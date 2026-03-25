"""Session save/restore orchestration — combines stacks + geometry."""

import json
import os
from typing import Optional

from engine.stacks.manager import StackManager
from engine.momentum.stack_persistence import serialize_stacks, deserialize_stacks
from engine.momentum.deferred_restore import DeferredRestore
from engine.momentum.geometry import capture_geometry, apply_geometry


_STACKS_FILE = "stacks.json"
_GEOMETRY_FILE = "geometry.json"


def save_session(
    manager: StackManager,
    session_dir: str,
    pane_dimensions: dict = None,
) -> None:
    """Persist stack state and geometry into *session_dir*.

    Creates the directory if it does not exist.  Writes two files:

    - ``stacks.json``  — serialised tab-stack data
    - ``geometry.json`` — proportional pane geometry
    """
    os.makedirs(session_dir, exist_ok=True)

    # --- stacks ---
    stacks_data = serialize_stacks(manager)
    with open(os.path.join(session_dir, _STACKS_FILE), "w") as f:
        json.dump(stacks_data, f, indent=2)

    # --- geometry ---
    pane_ids = list(manager.all_stacks().keys())
    geo_data = capture_geometry(pane_ids, pane_dimensions)
    with open(os.path.join(session_dir, _GEOMETRY_FILE), "w") as f:
        json.dump(geo_data, f, indent=2)


def restore_session(
    manager: StackManager,
    session_dir: str,
) -> DeferredRestore:
    """Load session data and return a ``DeferredRestore`` for lazy tab attach.

    Reads ``stacks.json`` (if present) and populates *manager*.
    Each stack's tabs are also queued in the returned ``DeferredRestore``
    so they can be applied once the physical panes are created.

    ``geometry.json`` is not applied here — the caller retrieves it
    separately via :func:`load_geometry` when ready to resize.
    """
    deferred = DeferredRestore()

    stacks_path = os.path.join(session_dir, _STACKS_FILE)
    if not os.path.isfile(stacks_path):
        return deferred

    with open(stacks_path, "r") as f:
        stacks_data = json.load(f)

    deserialize_stacks(stacks_data, manager)

    # Queue every stack's tabs for deferred physical restoration
    for pane_id, stack in manager.all_stacks().items():
        if stack.tabs:
            deferred.queue_restore(pane_id, list(stack.tabs))

    return deferred


def load_geometry(session_dir: str) -> dict:
    """Load saved geometry from *session_dir*.

    Returns an empty dict if the file is missing.
    """
    geo_path = os.path.join(session_dir, _GEOMETRY_FILE)
    if not os.path.isfile(geo_path):
        return {}
    with open(geo_path, "r") as f:
        return json.load(f)
