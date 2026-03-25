"""Tab bar renderer for tmux pane-border-format strings."""

from engine.stacks.stack import TabStack


def render_tab_bar(stack: TabStack, mode: str = "always") -> str:
    """Render a tmux-formatted tab bar string for a TabStack.

    Args:
        stack: The TabStack to render.
        mode: Display mode - "always", "on-demand", or "off".

    Returns:
        A tmux-formatted string suitable for pane-border-format.
    """
    if mode == "off":
        return ""

    if not stack.tabs:
        return ""

    if mode == "on-demand" and len(stack.tabs) <= 1:
        return ""

    parts = []
    for i, tab in enumerate(stack.tabs):
        # Determine label: role if present, otherwise first letter of capability_type
        if tab.role:
            label = tab.role
        else:
            label = tab.capability_type[0] if tab.capability_type else "?"

        # Determine style based on whether this tab is the active one
        if i == stack.active_index:
            parts.append(f"#[fg=cyan,bold][{label}]#[default]")
        else:
            parts.append(f"#[fg=white,dim][{label}]#[default]")

    return " ".join(parts)


def render_for_pane(stack: TabStack, config: dict) -> str:
    """Render tab bar using configuration from a config dict.

    Args:
        stack: The TabStack to render.
        config: Configuration dict; reads the "tabbar" key which should
                contain a dict with a "mode" key.

    Returns:
        A tmux-formatted string suitable for pane-border-format.
    """
    tabbar_config = config.get("tabbar", {"mode": "always"})
    mode = tabbar_config.get("mode", "always")
    return render_tab_bar(stack, mode=mode)
