"""
Menu handler for the Command Graph landing page (Alt+m).

Provides functions to build menu items from CommandGraphNode trees,
open the system root menu, and handle node selection.
"""

import logging
import os
from typing import List, Dict, Any, Optional

import yaml

logger = logging.getLogger(__name__)

from engine.graph.node import CommandGraphNode, NodeType, ActionKind, Scope
from engine.graph.loader import load_nodes_from_yaml, load_nodes_from_directory
from engine.graph.resolver import resolve_tree


# Path to the system root menu YAML, relative to the core/ directory
_SYSTEM_ROOT_YAML = os.path.join(
    os.path.dirname(__file__), "..", "..", "ui", "menus", "system_root.yaml"
)

# Profile-level menu directory
_PROFILE_MENU_DIR = os.path.expanduser("~/.config/nexus-shell/menus")

# Pack definitions directory
_PACKS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "engine", "packs", "examples"
)


def build_menu_items(
    nodes: List[CommandGraphNode], depth: int = 0
) -> List[Dict[str, Any]]:
    """Flatten a node tree into a list of menu-renderable items.

    Groups show their children indented at depth+1.
    Live source nodes include a ``resolver`` field.
    Setting nodes include a ``config_file`` field.
    """
    items: List[Dict[str, Any]] = []
    for node in nodes:
        item: Dict[str, Any] = {
            "id": node.id,
            "label": node.label,
            "type": node.type.value,
            "depth": depth,
            "icon": node.icon,
            "has_children": bool(node.children),
        }
        if node.type == NodeType.LIVE_SOURCE and node.resolver:
            item["resolver"] = node.resolver
        if node.type == NodeType.SETTING and node.config_file:
            item["config_file"] = node.config_file
        items.append(item)
        if node.children:
            items.extend(build_menu_items(node.children, depth + 1))
    return items


def _build_node_index(
    nodes: List[CommandGraphNode],
) -> Dict[str, CommandGraphNode]:
    """Recursively index all nodes by ID."""
    index: Dict[str, CommandGraphNode] = {}
    for node in nodes:
        index[node.id] = node
        if node.children:
            index.update(_build_node_index(node.children))
    return index


def _pack_commands_to_nodes(pack_yaml_path: str) -> List[CommandGraphNode]:
    """Read a pack YAML and convert its menu_nodes into CommandGraphNodes."""
    if not os.path.isfile(pack_yaml_path):
        return []
    try:
        with open(pack_yaml_path, "r") as f:
            data = yaml.safe_load(f)
    except Exception:
        logger.warning("Failed to parse pack YAML: %s", pack_yaml_path, exc_info=True)
        return []

    if not isinstance(data, dict):
        return []

    menu_nodes = data.get("menu_nodes", [])
    if not isinstance(menu_nodes, list):
        return []

    nodes: List[CommandGraphNode] = []
    for entry in menu_nodes:
        try:
            nodes.append(CommandGraphNode(
                id=entry["id"],
                label=entry.get("label", ""),
                type=NodeType.ACTION,
                scope=Scope.WORKSPACE,
                action_kind=ActionKind.SHELL,
                command=entry.get("command"),
                source_file=pack_yaml_path,
            ))
        except Exception:
            logger.warning("Failed to parse pack menu node in %s", pack_yaml_path, exc_info=True)
    return nodes


def _get_workspace_root() -> Optional[str]:
    """Determine workspace root from env vars or cwd."""
    root = os.environ.get("NEXUS_PROJECT_DIR") or os.environ.get("TMUX_PANE_CURRENT_PATH")
    if root and os.path.isdir(root):
        return root
    return os.getcwd()


def handle_open() -> Dict[str, Any]:
    """Load the cascaded menu tree and return renderable items.

    Loads nodes from three scope layers (global, profile, workspace)
    plus active pack commands, merges via resolve_tree, then flattens
    for rendering.  Returns a dict with action ``show_menu``, the
    flattened items list, and the source identifier.
    """
    # Layer 1: Global nodes from system_root.yaml
    yaml_path = os.path.normpath(_SYSTEM_ROOT_YAML)
    global_nodes = load_nodes_from_yaml(yaml_path) if os.path.isfile(yaml_path) else []

    # Layer 2: Profile nodes from ~/.config/nexus-shell/menus/
    profile_nodes = load_nodes_from_directory(_PROFILE_MENU_DIR, Scope.PROFILE)

    # Layer 3: Workspace nodes from .nexus/menus/ in workspace root
    workspace_root = _get_workspace_root()
    workspace_menu_dir = os.path.join(workspace_root, ".nexus", "menus") if workspace_root else ""
    workspace_nodes = load_nodes_from_directory(workspace_menu_dir, Scope.WORKSPACE) if workspace_menu_dir else []

    # Layer 3b: Active pack menu nodes (scope=WORKSPACE)
    active_pack = os.environ.get("NEXUS_PACK")
    if active_pack:
        pack_yaml = os.path.normpath(os.path.join(_PACKS_DIR, f"{active_pack}.yaml"))
        pack_nodes = _pack_commands_to_nodes(pack_yaml)
        workspace_nodes.extend(pack_nodes)

    # Merge via cascade resolver
    nodes = resolve_tree([global_nodes, profile_nodes, workspace_nodes])

    if not nodes and not os.path.isfile(yaml_path):
        return {
            "action": "show_menu",
            "items": [],
            "source": "system_root",
            "error": "no_menu_file",
        }

    items = build_menu_items(nodes)

    # Resolve live sources
    live_nodes = [
        {"node_id": item["id"], "resolver": item["resolver"]}
        for item in items
        if "resolver" in item
    ]
    if live_nodes:
        import asyncio
        from engine.graph.live_sources import resolve_all_live_sources
        try:
            resolved = asyncio.run(resolve_all_live_sources(live_nodes))
            for item in items:
                if item["id"] in resolved:
                    item["value"] = resolved[item["id"]]
        except Exception:
            logger.warning("Failed to resolve live sources for menu", exc_info=True)

    return {"action": "show_menu", "items": items, "source": "system_root"}


def handle_select(
    node_id: str, mode: str = "new_tab", nodes: Optional[List[CommandGraphNode]] = None
) -> Dict[str, Any]:
    """Handle selection of a node from the menu.

    Parameters
    ----------
    node_id:
        The ``id`` of the selected CommandGraphNode.
    mode:
        Interaction mode -- ``"new_tab"`` (Enter), ``"replace"`` (Shift+Enter),
        or ``"edit"`` (Opt+E).
    nodes:
        Optional pre-loaded node list.  When *None*, nodes are loaded from
        the system root YAML.
    """
    if nodes is None:
        yaml_path = os.path.normpath(_SYSTEM_ROOT_YAML)
        nodes = load_nodes_from_yaml(yaml_path)

    index = _build_node_index(nodes)
    node = index.get(node_id)

    if node is None:
        return {"error": "node_not_found", "node_id": node_id}

    if mode == "edit" and node.type == NodeType.SETTING:
        return {
            "action": "edit",
            "node_id": node_id,
            "config_file": node.config_file,
        }

    return {
        "action": "exec",
        "mode": mode,
        "node_id": node_id,
        "command": node.command,
    }
