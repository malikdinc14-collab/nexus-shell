"""Serialize and deserialize tab stack state for momentum save/restore."""

from typing import Dict, Any

from engine.stacks.stack import Tab, TabStack
from engine.stacks.manager import StackManager


_TAB_FIELDS = (
    "capability_type",
    "adapter_name",
    "command",
    "cwd",
    "role",
    "env",
    "is_active",
)


def _serialize_tab(tab: Tab) -> dict:
    """Convert a Tab to a JSON-safe dict, omitting ephemeral tmux_pane_id."""
    return {
        "id": tab.id,
        "capability_type": tab.capability_type,
        "adapter_name": tab.adapter_name,
        "command": tab.command,
        "cwd": tab.cwd,
        "role": tab.role,
        "env": dict(tab.env),
        "is_active": tab.is_active,
    }


def _deserialize_tab(data: dict) -> Tab:
    """Reconstruct a Tab from saved data.  tmux_pane_id is left as None."""
    return Tab(
        id=data.get("id", ""),
        capability_type=data["capability_type"],
        adapter_name=data["adapter_name"],
        command=data.get("command", ""),
        cwd=data.get("cwd", ""),
        role=data.get("role"),
        env=data.get("env", {}),
        is_active=data.get("is_active", False),
        tmux_pane_id=None,
    )


def serialize_stacks(manager: StackManager) -> dict:
    """Convert all stacks in *manager* to a JSON-safe dict.

    Structure::

        {
            "<pane_id>": {
                "id": "<stack uuid>",
                "role": "<optional role>",
                "active_index": 0,
                "tabs": [ { ... }, ... ]
            },
            ...
        }
    """
    result: Dict[str, Any] = {}
    for pane_id, stack in manager.all_stacks().items():
        result[pane_id] = {
            "id": stack.id,
            "role": stack.role,
            "active_index": stack.active_index,
            "tabs": [_serialize_tab(t) for t in stack.tabs],
        }
    return result


def deserialize_stacks(data: dict, manager: StackManager) -> None:
    """Restore stacks from *data* into *manager*.

    Existing stacks in *manager* are **not** cleared first — the caller
    should start with a fresh StackManager or clear it beforehand.
    """
    for pane_id, stack_data in data.items():
        stack = manager.get_or_create(pane_id)
        stack.id = stack_data.get("id", stack.id)
        stack.role = stack_data.get("role")
        tabs = [_deserialize_tab(td) for td in stack_data.get("tabs", [])]
        stack.tabs = tabs
        stack.active_index = stack_data.get("active_index", 0)
        # Assign pane_id to each tab so they know where they live
        for tab in stack.tabs:
            tab.tmux_pane_id = pane_id
