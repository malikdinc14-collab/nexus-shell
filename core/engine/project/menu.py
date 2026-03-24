"""Project menu loader — converts `.nexus/menu.yaml` to Command Graph nodes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from engine.graph.node import CommandGraphNode, NodeType, ActionKind, Scope

logger = logging.getLogger(__name__)


def load_project_menu(path: str | Path) -> List[CommandGraphNode]:
    """Load project menu commands from a `.nexus/menu.yaml` file.

    The menu.yaml format is simplified compared to the full Command Graph YAML:

    ```yaml
    commands:
      - id: run-tests
        label: "Run Tests"
        run: "pytest -x"
        key: Alt+t
        description: "Run test suite"
        confirm: true
        icon: "test"
        tags: [testing]
    ```

    Returns Command Graph nodes stamped with workspace scope.
    """
    path = Path(path)
    if not path.is_file():
        return []

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to parse project menu at %s: %s", path, e)
        return []

    if not isinstance(data, dict):
        logger.warning("project menu.yaml must be a dict with 'commands' key")
        return []

    commands = data.get("commands", [])
    if not isinstance(commands, list):
        logger.warning("project menu.yaml 'commands' must be a list")
        return []

    nodes: List[CommandGraphNode] = []
    for entry in commands:
        node = _entry_to_node(entry, source_file=str(path))
        if node:
            nodes.append(node)

    logger.info("Loaded %d project menu commands from %s", len(nodes), path)
    return nodes


def _entry_to_node(
    entry: Dict[str, Any], source_file: Optional[str] = None
) -> Optional[CommandGraphNode]:
    """Convert a simplified menu entry to a CommandGraphNode."""
    if not isinstance(entry, dict):
        return None

    entry_id = entry.get("id")
    if not entry_id:
        logger.warning("Project menu entry missing 'id', skipping")
        return None

    run_cmd = entry.get("run")
    if not run_cmd:
        logger.warning("Project menu entry '%s' missing 'run', skipping", entry_id)
        return None

    # Prefix project commands to avoid ID collisions with global commands
    node_id = f"project:{entry_id}"

    return CommandGraphNode(
        id=node_id,
        label=entry.get("label", entry_id),
        type=NodeType.ACTION,
        scope=Scope.WORKSPACE,
        action_kind=ActionKind.SHELL,
        command=run_cmd,
        tags=entry.get("tags", []) + ["project"],
        icon=entry.get("icon"),
        description=entry.get("description"),
        source_file=source_file,
    )
