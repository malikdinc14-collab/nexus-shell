"""HUD tab stack awareness — status line content for tab stacks."""

from typing import Dict

try:
    from engine.stacks.stack import TabStack
except ImportError:
    TabStack = None  # type: ignore


def format_tab_indicator(stack) -> str:
    """Format a compact status string for a single TabStack.

    Returns:
        - Single uppercase letter if only 1 tab (e.g. ``E``)
        - Bracketed list with active tab uppercase if multiple (e.g. ``[E|t|c]``)
        - ``\u00b7`` if the stack is empty
    """
    if not stack.tabs:
        return "\u00b7"

    letters = []
    for i, tab in enumerate(stack.tabs):
        letter = tab.capability_type[0] if tab.capability_type else "?"
        if i == stack.active_index:
            letters.append(letter.upper())
        else:
            letters.append(letter.lower())

    if len(letters) == 1:
        return letters[0]

    return "[" + "|".join(letters) + "]"


def format_pane_status(stacks: Dict[str, "TabStack"]) -> str:
    """Format status for all panes.

    Returns a string like ``%1:E %2:[T|c] %3:e``.
    """
    parts = []
    for pane_id in sorted(stacks.keys()):
        indicator = format_tab_indicator(stacks[pane_id])
        parts.append(f"{pane_id}:{indicator}")
    return " ".join(parts)


def format_hud_line(
    stacks: Dict[str, "TabStack"],
    profile_name: str = "",
    pack_count: int = 0,
) -> str:
    """Return a full HUD-ready status line.

    Format: ``[tabs] | profile: <name> | packs: <n>``
    Sections with no data are omitted.
    """
    sections = []

    if stacks:
        sections.append(format_pane_status(stacks))

    if profile_name:
        sections.append(f"profile: {profile_name}")

    if pack_count > 0:
        sections.append(f"packs: {pack_count}")

    return " | ".join(sections)
