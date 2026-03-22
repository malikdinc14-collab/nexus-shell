import os
import logging
from typing import List, Dict, Any, Optional

import yaml

from engine.graph.node import CommandGraphNode, NodeType, ActionKind, Scope

logger = logging.getLogger(__name__)


def _parse_node(data: Dict[str, Any], source_file: Optional[str] = None) -> CommandGraphNode:
    """Parse a dictionary into a CommandGraphNode, recursing into children."""
    node_type = NodeType(data["type"])
    action_kind = ActionKind(data["action_kind"]) if data.get("action_kind") else None
    scope = Scope(data["scope"]) if data.get("scope") else Scope.GLOBAL

    children = []
    if "children" in data and isinstance(data["children"], list):
        children = [_parse_node(c, source_file=source_file) for c in data["children"]]

    return CommandGraphNode(
        id=data["id"],
        label=data.get("label", ""),
        type=node_type,
        scope=scope,
        action_kind=action_kind,
        command=data.get("command"),
        children=children,
        resolver=data.get("resolver"),
        timeout_ms=data.get("timeout_ms", 3000),
        cache_ttl_s=data.get("cache_ttl_s", 30),
        config_file=data.get("config_file"),
        tags=data.get("tags", []),
        icon=data.get("icon"),
        description=data.get("description"),
        disabled=data.get("disabled", False),
        source_file=source_file,
    )


def load_nodes_from_yaml(path: str) -> List[CommandGraphNode]:
    """Load CommandGraphNode list from a YAML file.

    Returns empty list on missing file or invalid YAML.
    """
    if not os.path.isfile(path):
        logger.warning("YAML file not found: %s", path)
        return []

    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to parse YAML file %s: %s", path, e)
        return []

    if not isinstance(data, list):
        logger.warning("Expected a list in YAML file %s", path)
        return []

    nodes = []
    for entry in data:
        try:
            nodes.append(_parse_node(entry, source_file=path))
        except Exception as e:
            logger.warning("Failed to parse node in %s: %s", path, e)
    return nodes


def _stamp_scope(node: CommandGraphNode, scope: Scope) -> None:
    """Recursively stamp a scope onto a node and its children."""
    node.scope = scope
    for child in node.children:
        _stamp_scope(child, scope)


def load_nodes_from_directory(dir_path: str, scope: Scope) -> List[CommandGraphNode]:
    """Load all *.yaml files from a directory, stamping each node with the given scope.

    Returns merged list of all nodes across files.
    """
    if not os.path.isdir(dir_path):
        logger.warning("Directory not found: %s", dir_path)
        return []

    all_nodes: List[CommandGraphNode] = []
    for filename in sorted(os.listdir(dir_path)):
        if filename.endswith(".yaml"):
            filepath = os.path.join(dir_path, filename)
            nodes = load_nodes_from_yaml(filepath)
            for node in nodes:
                _stamp_scope(node, scope)
            all_nodes.extend(nodes)
    return all_nodes
