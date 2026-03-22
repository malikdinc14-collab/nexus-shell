"""tmux event hook command generator for StackManager integration.

This module generates tmux hook command strings. It does NOT execute
any tmux commands -- the generated strings are meant to be sourced
by the tmux config or run by the installer.
"""

from typing import List


def generate_hook_commands(nexus_home: str) -> List[str]:
    """Generate tmux hook commands for pane lifecycle events.

    Args:
        nexus_home: Absolute path to the nexus-shell installation directory.

    Returns:
        A list of tmux set-hook command strings.
    """
    return [
        f"set-hook -g after-split-window 'run-shell \"{nexus_home}/nexus-ctl stack create-anonymous #{{pane_id}}\"'",
        f"set-hook -g pane-died 'run-shell \"{nexus_home}/nexus-ctl stack cleanup #{{pane_id}}\"'",
        f"set-hook -g after-kill-pane 'run-shell \"{nexus_home}/nexus-ctl stack cleanup #{{pane_id}}\"'",
    ]


def generate_pane_border_refresh(nexus_home: str) -> str:
    """Generate the tmux pane-border-format setting for tab bar rendering.

    Args:
        nexus_home: Absolute path to the nexus-shell installation directory.

    Returns:
        A tmux set command string for pane-border-format.
    """
    return f'set -g pane-border-format "#(python3 {nexus_home}/core/engine/stacks/render_border.py #{{pane_id}})"'


def install_hooks(nexus_home: str) -> List[str]:
    """Generate all tmux commands needed for stack integration.

    Combines hook commands and border format into a single list.

    Args:
        nexus_home: Absolute path to the nexus-shell installation directory.

    Returns:
        A combined list of all tmux command strings to install.
    """
    commands = generate_hook_commands(nexus_home)
    commands.append(generate_pane_border_refresh(nexus_home))
    return commands
