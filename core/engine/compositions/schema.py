"""Unified composition schema handler.

Normalizes two JSON schema variants used in core/ui/compositions/:
  - Type-based:      {"type": "hsplit"/"vsplit", "panes": [...], "id", "size" (int)}
  - Direction-based: {"direction": "horizontal"/"vertical", "panes": [...], "size" ("65%")}
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CompositionPane:
    role: str                          # "editor", "terminal", "explorer", "chat", etc.
    width_pct: float = 50.0           # Percentage of parent width
    height_pct: float = 100.0         # Percentage of parent height
    command: Optional[str] = None     # Override command
    split: str = "h"                  # "h" (horizontal) or "v" (vertical)


@dataclass
class Composition:
    name: str
    description: str = ""
    panes: List[CompositionPane] = field(default_factory=list)
    source_file: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_size(raw) -> float:
    """Convert a size value (int, float, or '65%' string) to a float percentage."""
    if raw is None:
        return 50.0
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        return float(raw.rstrip("%"))
    return 50.0


def _split_char(direction_or_type: str) -> str:
    """Return 'h' or 'v' from either schema's split indicator."""
    val = direction_or_type.lower()
    if val in ("hsplit", "horizontal"):
        return "h"
    if val in ("vsplit", "vertical"):
        return "v"
    return "h"


def _is_direction_schema(layout: dict) -> bool:
    return "direction" in layout


def _flatten_panes(node: dict, parent_split: str, parent_width: float, parent_height: float) -> List[CompositionPane]:
    """Recursively flatten a layout tree into a list of CompositionPane."""
    panes: List[CompositionPane] = []

    if _is_direction_schema(node):
        split = _split_char(node.get("direction", "horizontal"))
        children = node.get("panes", [])
    else:
        split = _split_char(node.get("type", "hsplit"))
        children = node.get("panes", [])

    if not children:
        # Leaf pane
        role = node.get("id", node.get("title", "pane"))
        panes.append(CompositionPane(
            role=role,
            width_pct=parent_width,
            height_pct=parent_height,
            command=node.get("command"),
            split=parent_split,
        ))
        return panes

    n = len(children)
    for child in children:
        child_size = _parse_size(child.get("size"))
        if split == "h":
            w = child_size
            h = parent_height
        else:
            w = parent_width
            h = child_size

        child_has_children = "panes" in child
        if child_has_children:
            panes.extend(_flatten_panes(child, split, w, h))
        else:
            role = child.get("id", child.get("title", "pane"))
            panes.append(CompositionPane(
                role=role,
                width_pct=w,
                height_pct=h,
                command=child.get("command"),
                split=split,
            ))

    return panes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_composition(path: str) -> Optional[Composition]:
    """Read a composition JSON file, handling both schema variants.

    Returns None on any error (missing file, bad JSON, etc.).
    """
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    name = data.get("name", os.path.splitext(os.path.basename(path))[0])
    description = data.get("description", "")
    layout = data.get("layout", {})

    panes = _flatten_panes(layout, "h", 100.0, 100.0)

    return Composition(
        name=name,
        description=description,
        panes=panes,
        source_file=path,
    )


def load_compositions_from_directory(dir_path: str) -> List[Composition]:
    """Scan *dir_path* for *.json files, return list of valid Composition objects."""
    compositions: List[Composition] = []
    if not os.path.isdir(dir_path):
        return compositions
    for entry in sorted(os.listdir(dir_path)):
        if not entry.endswith(".json"):
            continue
        full = os.path.join(dir_path, entry)
        comp = load_composition(full)
        if comp is not None:
            comp.source_file = full
            compositions.append(comp)
    return compositions


def list_composition_names(dir_path: str) -> List[str]:
    """Quick scan returning just composition names (filename without .json)."""
    if not os.path.isdir(dir_path):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(dir_path)
        if f.endswith(".json")
    )
