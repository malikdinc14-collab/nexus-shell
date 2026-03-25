"""HUD Renderer — formats module results for tmux status bar."""
from typing import List

from engine.hud.module import resolve_module


def render_hud_line(module_ids: List[str], separator: str = " | ") -> str:
    """Resolve all modules and format into a status line string."""
    parts = []
    for mid in module_ids:
        if mid == "tabs":
            # Special case — tab indicator handled separately
            parts.append("[tabs]")
            continue
        result = resolve_module(mid)
        if result.icon:
            parts.append(f"{result.icon}:{result.text}")
        else:
            parts.append(result.text)
    return separator.join(parts)


def render_tmux_status(module_ids: List[str]) -> str:
    """Generate a tmux status-right format string with HUD modules."""
    # tmux uses #() for shell commands — we generate a static string
    return render_hud_line(module_ids)
