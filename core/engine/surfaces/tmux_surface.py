"""
TmuxSurface — Surface implementation that dispatches to tmux.

Accepts a callable `run_tmux(args, socket_label) -> str|None` so the daemon
can inject its own tmux runner (with logging, socket resolution, etc.)
instead of spawning subprocesses directly.
"""

import logging
import subprocess
from typing import Callable, Dict, List, Optional

from engine.surfaces import (
    Surface,
    SplitDirection,
    Dimensions,
    ContainerInfo,
    MenuItem,
    HudModule,
)

logger = logging.getLogger(__name__)

# Type alias for the tmux command runner function.
# Signature: run_tmux(args: list[str], socket_label: str|None) -> str|None
TmuxRunner = Callable[[list, Optional[str]], Optional[str]]


def _default_runner(args: list, socket_label: Optional[str] = None) -> Optional[str]:
    """Standalone tmux runner for use outside the daemon."""
    cmd = ["tmux"]
    if socket_label:
        if socket_label.startswith("/"):
            cmd += ["-S", socket_label]
        else:
            cmd += ["-L", socket_label]
    cmd += args
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        return result.stdout.decode("utf-8", errors="replace").strip()
    except subprocess.CalledProcessError:
        return None


class TmuxSurface(Surface):
    """Surface implementation backed by tmux.

    Parameters
    ----------
    run_tmux:
        Callable that executes tmux commands. If None, uses a default
        subprocess runner. The daemon injects its own runner so commands
        go through the daemon's logging and socket resolution.
    socket_label:
        Default tmux socket label (e.g. ``"nexus_myproject"``).
    """

    def __init__(
        self,
        run_tmux: Optional[TmuxRunner] = None,
        socket_label: Optional[str] = None,
    ):
        self._run = run_tmux or _default_runner
        self._socket_label = socket_label

    def _tmux(self, args: list) -> Optional[str]:
        """Execute a tmux command through the runner."""
        return self._run(args, self._socket_label)

    # -- Lifecycle -------------------------------------------------------------

    def initialize(self, session_name: str, cwd: str = "") -> str:
        args = ["new-session", "-d", "-s", session_name, "-P", "-F", "#{session_id}"]
        if cwd:
            args += ["-c", cwd]
        result = self._tmux(args)
        return result or session_name

    def teardown(self, session: str) -> None:
        self._tmux(["kill-session", "-t", session])

    # -- Spatial — container management ----------------------------------------

    def create_container(self, session: str, command: str = "",
                         cwd: str = "") -> str:
        args = ["new-window", "-t", session, "-P", "-F", "#{pane_id}"]
        if cwd:
            args += ["-c", cwd]
        if command:
            args.append(command)
        result = self._tmux(args)
        return result or ""

    def split(self, handle: str, direction: SplitDirection,
              size: Optional[int] = None, cwd: str = "") -> str:
        flag = "-h" if direction == SplitDirection.HORIZONTAL else "-v"
        args = ["split-window", flag, "-t", handle, "-P", "-F", "#{pane_id}"]
        if size is not None:
            args += ["-l", str(size)]
        if cwd:
            args += ["-c", cwd]
        result = self._tmux(args)
        return result or ""

    def destroy_container(self, handle: str) -> None:
        self._tmux(["kill-pane", "-t", handle])

    def focus(self, handle: str) -> None:
        self._tmux(["select-pane", "-t", handle])

    def resize(self, handle: str, dimensions: Dimensions) -> None:
        self._tmux(["resize-pane", "-t", handle,
                     "-x", str(dimensions.width), "-y", str(dimensions.height)])

    # -- Swap — atomic container exchange --------------------------------------

    def swap_containers(self, source: str, target: str) -> bool:
        """Atomically swap two panes (ghost-swap).

        Validates both panes exist before issuing swap-pane.
        Uses -d flag to keep focus on the original position.
        """
        if source == target:
            return True

        all_panes = self._tmux(["list-panes", "-a", "-F", "#{pane_id}"])
        pane_list = all_panes.split("\n") if all_panes else []

        if source not in pane_list:
            logger.error(
                "[INVARIANT] swap_containers source '%s' does not exist. "
                "Target: '%s'. Live panes: %s", source, target, pane_list,
            )
            return False

        if target not in pane_list:
            logger.error(
                "[INVARIANT] swap_containers target '%s' does not exist. "
                "Source: '%s'. Live panes: %s", target, source, pane_list,
            )
            return False

        result = self._tmux(["swap-pane", "-d", "-s", source, "-t", target])
        if result is None:
            logger.error(
                "[INVARIANT] swap-pane failed despite both panes existing. "
                "Source: '%s', Target: '%s'", source, target,
            )
            return False
        return True

    def container_exists(self, handle: str) -> bool:
        if not handle or handle == "null":
            return False
        all_panes = self._tmux(["list-panes", "-a", "-F", "#{pane_id}"])
        pane_list = all_panes.split("\n") if all_panes else []
        return handle in pane_list

    # -- Content — process management ------------------------------------------

    def attach_process(self, handle: str, command: str) -> None:
        self._tmux(["send-keys", "-t", handle, command, "Enter"])

    def send_input(self, handle: str, keys: str) -> None:
        self._tmux(["send-keys", "-t", handle, keys])

    # -- State — query containers ----------------------------------------------

    def list_containers(self, session: str) -> List[ContainerInfo]:
        fmt = "#{pane_id}\t#{pane_index}\t#{pane_width}\t#{pane_height}\t#{pane_left}\t#{pane_top}\t#{pane_current_command}\t#{pane_title}\t#{pane_active}"
        result = self._tmux(["list-panes", "-t", session, "-F", fmt])
        if not result:
            return []
        containers = []
        for line in result.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) < 9:
                continue
            containers.append(ContainerInfo(
                handle=parts[0],
                index=int(parts[1]),
                width=int(parts[2]),
                height=int(parts[3]),
                x=int(parts[4]),
                y=int(parts[5]),
                command=parts[6],
                title=parts[7],
                focused=(parts[8] == "1"),
            ))
        return containers

    def get_focused(self, session: str) -> Optional[str]:
        result = self._tmux([
            "display-message", "-t", session, "-p", "#{pane_id}",
        ])
        return result if result else None

    def get_dimensions(self, handle: str) -> Dimensions:
        result = self._tmux([
            "display-message", "-t", handle, "-p", "#{pane_width},#{pane_height}",
        ])
        if result and "," in result:
            w, h = result.split(",", 1)
            return Dimensions(width=int(w), height=int(h))
        return Dimensions(width=80, height=24)

    def get_geometry(self, handle: str):
        result = self._tmux([
            "display-message", "-t", handle, "-p",
            "#{pane_left},#{pane_top},#{pane_width},#{pane_height}",
        ])
        if not result:
            return None
        parts = result.split(",")
        if len(parts) < 4:
            return None
        return {
            "x": int(parts[0]), "y": int(parts[1]),
            "w": int(parts[2]), "h": int(parts[3]),
        }

    def set_geometry(self, handle: str, geometry: dict) -> None:
        self._tmux([
            "resize-pane", "-t", handle,
            "-x", str(geometry["w"]), "-y", str(geometry["h"]),
        ])

    # -- Metadata — tag containers ---------------------------------------------

    def set_tag(self, handle: str, key: str, value: str) -> None:
        self._tmux(["set-option", "-p", "-t", handle, f"@{key}", value])

    def get_tag(self, handle: str, key: str) -> str:
        result = self._tmux([
            "display-message", "-p", "-t", handle, f"#{{@{key}}}",
        ])
        return result if result else ""

    def set_title(self, handle: str, title: str) -> None:
        self._tmux([
            "select-pane", "-t", handle, "-T", title,
        ])

    # -- Rendering — menus, HUD, notifications ---------------------------------

    def show_menu(self, items: List[MenuItem],
                  prompt: str = "Select:") -> Optional[str]:
        # Menu rendering is handled by external scripts (menu-popup.sh / fzf).
        # The surface returns None — the engine dispatches via CLI, not surface.
        return None

    def show_hud(self, modules: List[HudModule]) -> None:
        # HUD is rendered by tmux status-line — updates go through
        # tmux set-option status-right, handled by the HUD renderer.
        pass

    def notify(self, message: str, level: str = "info") -> None:
        self._tmux(["display-message", message])

    # -- Layout ----------------------------------------------------------------

    def apply_layout(self, session: str, layout: dict) -> bool:
        # Layout application is handled by WorkspaceOrchestrator.
        # Future: this method can delegate to the orchestrator.
        return False

    def capture_layout(self, session: str) -> dict:
        containers = self.list_containers(session)
        return {
            "containers": [
                {
                    "handle": c.handle,
                    "width": c.width,
                    "height": c.height,
                    "x": c.x,
                    "y": c.y,
                    "command": c.command,
                }
                for c in containers
            ]
        }

    # -- Environment -----------------------------------------------------------

    def set_env(self, session: str, key: str, value: str) -> None:
        self._tmux(["set-environment", "-t", session, key, value])
