import os
from typing import List

from engine.packs.pack import Pack


def detect_markers(project_root: str) -> List[str]:
    """Scan project_root for known marker files.

    Returns list of found marker filenames (e.g., ["pyproject.toml", "Dockerfile"]).
    """
    if not os.path.isdir(project_root):
        return []
    found = []
    for entry in os.listdir(project_root):
        full = os.path.join(project_root, entry)
        if os.path.isfile(full):
            found.append(entry)
    return found


def suggest_packs(project_root: str, available_packs: List[Pack]) -> List[Pack]:
    """Cross-reference detected markers with pack markers.

    Returns list of packs whose markers match (ANY marker found = match).
    Sorts by number of matching markers (most matches first).
    NEVER auto-enables -- returns suggestions only.
    """
    markers = set(detect_markers(project_root))
    scored: List[tuple] = []
    for pack in available_packs:
        matches = len(markers.intersection(pack.markers))
        if matches > 0:
            scored.append((matches, pack))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [pack for _, pack in scored]
