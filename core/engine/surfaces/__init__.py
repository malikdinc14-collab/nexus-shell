"""
Surface abstraction — the display/control layer for Nexus Shell.

A Surface is anything that can host workspaces: a terminal multiplexer,
a tiling window manager, a desktop app, or a web browser. The core
never calls tmux, i3, or any display technology directly — it talks
to a Surface.

Current implementations: NullSurface, TextualSurface
Planned: SwaySurface, HyprlandSurface, TauriSurface, WebSurface, CompositeSurface
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class SplitDirection(Enum):
    HORIZONTAL = "h"
    VERTICAL = "v"


@dataclass
class Dimensions:
    width: int
    height: int


@dataclass
class ContainerInfo:
    """Surface-agnostic descriptor for a display container (pane/window/panel)."""
    handle: str
    index: int
    width: int
    height: int
    x: int = 0
    y: int = 0
    command: str = ""
    title: str = ""
    focused: bool = False
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MenuItem:
    """A renderable menu item."""
    id: str
    label: str
    icon: Optional[str] = None
    description: Optional[str] = None
    value: Optional[str] = None
    depth: int = 0
    has_children: bool = False


@dataclass
class HudModule:
    """A HUD status module."""
    id: str
    label: str
    value: str
    position: str = "right"  # "left", "right", "center"
    color: Optional[str] = None


class Surface(ABC):
    """Abstract base for all display surfaces.

    A Surface handles spatial layout, process attachment, menu rendering,
    HUD display, and notifications. The core calls Surface methods;
    implementations translate to tmux, Sway, Tauri IPC, WebSocket, etc.
    """

    # -- Lifecycle -------------------------------------------------------------

    @abstractmethod
    def initialize(self, session_name: str, cwd: str = "") -> str:
        """Create or attach to a workspace session. Returns session handle."""
        ...

    @abstractmethod
    def teardown(self, session: str) -> None:
        """Destroy a workspace session and all its containers."""
        ...

    # -- Spatial — container management ----------------------------------------

    @abstractmethod
    def create_container(self, session: str, command: str = "",
                         cwd: str = "") -> str:
        """Create a new container in the session. Returns container handle."""
        ...

    @abstractmethod
    def split(self, handle: str, direction: SplitDirection,
              size: Optional[int] = None, cwd: str = "") -> str:
        """Split a container. Returns new container handle."""
        ...

    @abstractmethod
    def destroy_container(self, handle: str) -> None:
        """Destroy a container and its contents."""
        ...

    @abstractmethod
    def focus(self, handle: str) -> None:
        """Move focus to a container."""
        ...

    @abstractmethod
    def resize(self, handle: str, dimensions: Dimensions) -> None:
        """Resize a container."""
        ...

    # -- Content — process management ------------------------------------------

    @abstractmethod
    def attach_process(self, handle: str, command: str) -> None:
        """Run a command inside a container."""
        ...

    @abstractmethod
    def send_input(self, handle: str, keys: str) -> None:
        """Send keystrokes to a container (like typing)."""
        ...

    # -- State — query containers ----------------------------------------------

    @abstractmethod
    def list_containers(self, session: str) -> List[ContainerInfo]:
        """Return all containers in the session."""
        ...

    @abstractmethod
    def get_focused(self, session: str) -> Optional[str]:
        """Return the handle of the currently focused container."""
        ...

    @abstractmethod
    def get_dimensions(self, handle: str) -> Dimensions:
        """Return dimensions of a container."""
        ...

    # -- Metadata — tag containers ---------------------------------------------

    @abstractmethod
    def set_tag(self, handle: str, key: str, value: str) -> None:
        """Attach metadata to a container (durable for session lifetime)."""
        ...

    @abstractmethod
    def get_tag(self, handle: str, key: str) -> str:
        """Retrieve metadata from a container."""
        ...

    @abstractmethod
    def set_title(self, handle: str, title: str) -> None:
        """Set the display title of a container."""
        ...

    # -- Rendering — menus, HUD, notifications ---------------------------------

    @abstractmethod
    def show_menu(self, items: List[MenuItem],
                  prompt: str = "Select:") -> Optional[str]:
        """Display a menu and return the selected item ID, or None."""
        ...

    @abstractmethod
    def show_hud(self, modules: List[HudModule]) -> None:
        """Update the HUD/status display with the given modules."""
        ...

    @abstractmethod
    def notify(self, message: str, level: str = "info") -> None:
        """Show a notification to the user."""
        ...

    # -- Layout ----------------------------------------------------------------

    @abstractmethod
    def apply_layout(self, session: str, layout: dict) -> bool:
        """Apply a composition layout to the session. Returns success."""
        ...

    @abstractmethod
    def capture_layout(self, session: str) -> dict:
        """Capture the current layout for persistence."""
        ...

    # -- Environment -----------------------------------------------------------

    @abstractmethod
    def set_env(self, session: str, key: str, value: str) -> None:
        """Set an environment variable visible to all containers."""
        ...


class NullSurface(Surface):
    """No-op surface for testing and headless operation.

    Every method returns an empty/None/False value without side effects.
    """

    def initialize(self, session_name: str, cwd: str = "") -> str:
        return f"null:{session_name}"

    def teardown(self, session: str) -> None:
        pass

    def create_container(self, session: str, command: str = "",
                         cwd: str = "") -> str:
        return f"{session}:container:0"

    def split(self, handle: str, direction: SplitDirection,
              size: Optional[int] = None, cwd: str = "") -> str:
        return f"{handle}:split"

    def destroy_container(self, handle: str) -> None:
        pass

    def focus(self, handle: str) -> None:
        pass

    def resize(self, handle: str, dimensions: Dimensions) -> None:
        pass

    def attach_process(self, handle: str, command: str) -> None:
        pass

    def send_input(self, handle: str, keys: str) -> None:
        pass

    def list_containers(self, session: str) -> List[ContainerInfo]:
        return []

    def get_focused(self, session: str) -> Optional[str]:
        return None

    def get_dimensions(self, handle: str) -> Dimensions:
        return Dimensions(width=0, height=0)

    def set_tag(self, handle: str, key: str, value: str) -> None:
        pass

    def get_tag(self, handle: str, key: str) -> str:
        return ""

    def set_title(self, handle: str, title: str) -> None:
        pass

    def show_menu(self, items: List[MenuItem],
                  prompt: str = "Select:") -> Optional[str]:
        return None

    def show_hud(self, modules: List[HudModule]) -> None:
        pass

    def notify(self, message: str, level: str = "info") -> None:
        pass

    def apply_layout(self, session: str, layout: dict) -> bool:
        return False

    def capture_layout(self, session: str) -> dict:
        return {}

    def set_env(self, session: str, key: str, value: str) -> None:
        pass


__all__ = [
    "Surface",
    "NullSurface",
    "SplitDirection",
    "Dimensions",
    "ContainerInfo",
    "MenuItem",
    "HudModule",
]
