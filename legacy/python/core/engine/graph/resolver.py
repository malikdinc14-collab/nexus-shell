import copy
from typing import List, Dict

from engine.graph.node import CommandGraphNode


def merge_node(base: CommandGraphNode, override: CommandGraphNode) -> CommandGraphNode:
    """Merge two nodes with the same id. Override wins for scalar fields.

    - Children merge recursively by child.id
    - Tags are unioned
    - disabled=True in override marks the node as disabled
    """
    merged = copy.deepcopy(base)

    # Override scalar fields when the override provides a non-default value
    merged.label = override.label if override.label else merged.label
    merged.type = override.type
    merged.scope = override.scope
    merged.action_kind = override.action_kind if override.action_kind is not None else merged.action_kind
    merged.command = override.command if override.command is not None else merged.command
    merged.resolver = override.resolver if override.resolver is not None else merged.resolver
    merged.timeout_ms = override.timeout_ms
    merged.cache_ttl_s = override.cache_ttl_s
    merged.config_file = override.config_file if override.config_file is not None else merged.config_file
    merged.icon = override.icon if override.icon is not None else merged.icon
    merged.description = override.description if override.description is not None else merged.description
    merged.disabled = override.disabled
    merged.source_file = override.source_file if override.source_file is not None else merged.source_file

    # Union tags
    merged.tags = list(set(merged.tags) | set(override.tags))

    # Merge children by id
    base_children: Dict[str, CommandGraphNode] = {c.id: c for c in merged.children}
    for oc in override.children:
        if oc.id in base_children:
            base_children[oc.id] = merge_node(base_children[oc.id], oc)
        else:
            base_children[oc.id] = copy.deepcopy(oc)
    merged.children = list(base_children.values())

    return merged


def _remove_disabled(nodes: List[CommandGraphNode]) -> List[CommandGraphNode]:
    """Recursively remove disabled nodes from a list."""
    result = []
    for node in nodes:
        if node.disabled:
            continue
        node.children = _remove_disabled(node.children)
        result.append(node)
    return result


def resolve_tree(scope_chain: List[List[CommandGraphNode]]) -> List[CommandGraphNode]:
    """Resolve a tree from multiple scope layers.

    Takes [global_nodes, profile_nodes, workspace_nodes] (or any number of layers).
    Merges by node ID across scopes; later scopes override earlier.
    Removes disabled nodes from the final result.
    Returns fully resolved tree.
    """
    if not scope_chain:
        return []

    # Build merged index layer by layer
    merged: Dict[str, CommandGraphNode] = {}

    for layer in scope_chain:
        for node in layer:
            if node.id in merged:
                merged[node.id] = merge_node(merged[node.id], node)
            else:
                merged[node.id] = copy.deepcopy(node)

    result = list(merged.values())
    return _remove_disabled(result)
