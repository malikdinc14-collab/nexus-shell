"""Connector Engine — reads connector definitions and wires event-to-action automation."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml


@dataclass
class ConnectorDef:
    """A single connector definition linking a trigger event to an action."""

    name: str
    trigger_type: str  # Event type to subscribe to (e.g., "fs.file.saved")
    trigger_filter: Dict[str, str] = field(default_factory=dict)
    action_shell: Optional[str] = None
    action_internal: Optional[str] = None
    scope: str = "global"
    enabled: bool = True


def load_connectors_from_yaml(path: str) -> List[ConnectorDef]:
    """Read a connectors YAML file and return a list of ConnectorDef objects.

    Returns an empty list if the file is missing or contains invalid YAML.
    """
    if not os.path.isfile(path):
        return []

    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
        return []

    if not isinstance(data, dict) or "connectors" not in data:
        return []

    connectors: List[ConnectorDef] = []
    for entry in data["connectors"]:
        if not isinstance(entry, dict):
            continue

        trigger = entry.get("trigger", {})
        action = entry.get("action", {})

        connectors.append(
            ConnectorDef(
                name=entry.get("name", ""),
                trigger_type=trigger.get("type", ""),
                trigger_filter=trigger.get("filter", {}),
                action_shell=action.get("shell"),
                action_internal=action.get("internal"),
                scope=entry.get("scope", "global"),
                enabled=entry.get("enabled", True),
            )
        )

    return connectors


class ConnectorEngine:
    """Manages connector definitions and matches events to actions."""

    def __init__(self) -> None:
        self._connectors: List[ConnectorDef] = []

    def load(self, path: str) -> None:
        """Load connectors from a YAML file and add them to the internal list."""
        loaded = load_connectors_from_yaml(path)
        self._connectors.extend(loaded)

    def load_cascade(self, global_dir: str, workspace_dir: str = "") -> None:
        """Load connectors from global and workspace directories.

        Workspace connectors override global ones when they share the same name.
        """
        global_path = os.path.join(global_dir, "connectors.yaml")
        global_connectors = load_connectors_from_yaml(global_path)

        ws_connectors: List[ConnectorDef] = []
        if workspace_dir:
            ws_path = os.path.join(workspace_dir, "connectors.yaml")
            ws_connectors = load_connectors_from_yaml(ws_path)

        # Build a name->connector map; workspace overrides global by name
        merged: Dict[str, ConnectorDef] = {}
        for c in global_connectors:
            merged[c.name] = c
        for c in ws_connectors:
            merged[c.name] = c

        self._connectors.extend(merged.values())

    def match_event(
        self, event_type: str, event_data: dict = {}
    ) -> List[ConnectorDef]:
        """Return all enabled connectors whose trigger matches the given event.

        Matching rules:
        - trigger_type must equal event_type, or be a wildcard pattern
          (e.g., "fs.*" matches "fs.file.saved")
        - All trigger_filter keys must match corresponding event_data values
        """
        results: List[ConnectorDef] = []
        for c in self._connectors:
            if not c.enabled:
                continue
            # Check trigger type match (supports wildcard via fnmatch)
            if not fnmatch.fnmatch(event_type, c.trigger_type):
                continue
            # Check filter match
            if c.trigger_filter:
                match = True
                for key, pattern in c.trigger_filter.items():
                    value = event_data.get(key, "")
                    if not fnmatch.fnmatch(value, pattern):
                        match = False
                        break
                if not match:
                    continue
            results.append(c)
        return results

    def get_action(self, connector: ConnectorDef) -> dict:
        """Return the action descriptor for a connector."""
        if connector.action_shell is not None:
            return {"type": "shell", "command": connector.action_shell}
        return {"type": "internal", "command": connector.action_internal}

    @property
    def all_connectors(self) -> List[ConnectorDef]:
        """Return all loaded connectors."""
        return list(self._connectors)

    @property
    def enabled_connectors(self) -> List[ConnectorDef]:
        """Return only enabled connectors."""
        return [c for c in self._connectors if c.enabled]
