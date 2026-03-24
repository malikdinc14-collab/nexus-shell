"""
TextualSurface — Level 0 contained Surface using the Textual TUI framework.

All panes are internal widget divisions within a single terminal window.
Terminal processes run via PTY and render through pyte into Rich text.
Menus use Textual's OptionList, HUD uses Header/Footer, notifications
use Textual's built-in toast system.

This surface can also serve over the web via `textual-web`.
"""

from __future__ import annotations

import asyncio
import fcntl
import logging
import os
import pty
import signal
import struct
import termios
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pyte
from rich.text import Text

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.events import Key, Resize
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Footer,
    Header,
    Label,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option

from engine.surfaces import (
    ContainerInfo,
    Dimensions,
    HudModule,
    MenuItem,
    NullSurface,
    SplitDirection,
    Surface,
)

logger = logging.getLogger(__name__)

# ── PTY Pane Widget ──────────────────────────────────────────────────────────


PYTE_TO_RICH_COLORS = {
    "black": "black",
    "red": "red",
    "green": "green",
    "brown": "yellow",
    "blue": "blue",
    "magenta": "magenta",
    "cyan": "cyan",
    "white": "white",
    "default": "default",
}


@dataclass
class PaneState:
    """Tracks the state of one pane within the TextualSurface."""

    handle: str
    index: int
    command: str = ""
    title: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    pid: int = 0
    fd: int = -1
    screen: Optional[pyte.Screen] = None
    stream: Optional[pyte.Stream] = None
    focused: bool = False
    width: int = 80
    height: int = 24


class PtyPane(Static):
    """A widget that hosts a PTY-backed terminal process.

    Uses pyte to emulate a VT100 terminal and renders the screen buffer
    as Rich text on each update cycle.
    """

    DEFAULT_CSS = """
    PtyPane {
        width: 1fr;
        height: 1fr;
        overflow: hidden;
        border: solid $accent;
        padding: 0;
    }
    PtyPane.focused {
        border: solid $success;
    }
    """

    def __init__(
        self,
        pane_state: PaneState,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__("", id=id, classes=classes)
        self.pane_state = pane_state
        self._reader_task: Optional[asyncio.Task] = None

    def on_mount(self) -> None:
        if self.pane_state.command:
            self._spawn_process(self.pane_state.command)

    def _spawn_process(self, command: str) -> None:
        """Fork a PTY child process running `command`."""
        state = self.pane_state
        rows, cols = state.height, state.width

        state.screen = pyte.Screen(cols, rows)
        state.stream = pyte.Stream(state.screen)

        pid, fd = pty.openpty()

        # Set terminal size
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

        child_pid = os.fork()
        if child_pid == 0:
            # Child process
            os.close(fd)
            os.setsid()
            os.dup2(pid, 0)
            os.dup2(pid, 1)
            os.dup2(pid, 2)
            os.close(pid)
            os.environ["TERM"] = "xterm-256color"
            os.environ["COLUMNS"] = str(cols)
            os.environ["LINES"] = str(rows)
            os.execvp("/bin/sh", ["/bin/sh", "-c", command])
        else:
            os.close(pid)
            state.pid = child_pid
            state.fd = fd
            self._start_reader()

    @work(thread=True, exclusive=True, group="pty-read")
    def _start_reader(self) -> None:
        """Read PTY output in a background thread and feed to pyte."""
        state = self.pane_state
        fd = state.fd
        while True:
            try:
                data = os.read(fd, 4096)
                if not data:
                    break
                state.stream.feed(data.decode("utf-8", errors="replace"))
                self.call_from_thread(self._render_screen)
            except OSError:
                break

    def _render_screen(self) -> None:
        """Convert pyte screen buffer to Rich Text and update the widget."""
        screen = self.pane_state.screen
        if screen is None:
            return

        lines: list[Text] = []
        for row in range(screen.lines):
            line = Text()
            for col in range(screen.columns):
                char = screen.buffer[row][col]
                style_parts: list[str] = []
                fg = PYTE_TO_RICH_COLORS.get(char.fg, "default")
                bg = PYTE_TO_RICH_COLORS.get(char.bg, "default")
                if fg != "default":
                    style_parts.append(fg)
                if bg != "default":
                    style_parts.append(f"on {bg}")
                if char.bold:
                    style_parts.append("bold")
                if char.italics:
                    style_parts.append("italic")
                if char.underscore:
                    style_parts.append("underline")
                style = " ".join(style_parts) if style_parts else ""
                line.append(char.data, style=style)
            lines.append(line)

        combined = Text("\n").join(lines)
        self.update(combined)

    def on_key(self, event: Key) -> None:
        """Forward keystrokes to the PTY."""
        if self.pane_state.fd < 0:
            return
        char = event.character
        if char is not None:
            try:
                os.write(self.pane_state.fd, char.encode("utf-8"))
            except OSError:
                pass

    def on_resize(self, event: Resize) -> None:
        """Resize the PTY and pyte screen when the widget resizes."""
        state = self.pane_state
        w, h = event.size.width, event.size.height
        if w < 1 or h < 1:
            return
        state.width = w
        state.height = h
        if state.screen:
            state.screen.resize(h, w)
        if state.fd >= 0:
            try:
                winsize = struct.pack("HHHH", h, w, 0, 0)
                fcntl.ioctl(state.fd, termios.TIOCSWINSZ, winsize)
                if state.pid:
                    os.kill(state.pid, signal.SIGWINCH)
            except OSError:
                pass

    def cleanup(self) -> None:
        """Kill the child process and close the PTY fd."""
        state = self.pane_state
        if state.pid:
            try:
                os.kill(state.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            state.pid = 0
        if state.fd >= 0:
            try:
                os.close(state.fd)
            except OSError:
                pass
            state.fd = -1


# ── HUD Bar Widget ──────────────────────────────────────────────────────────


class HudBar(Horizontal):
    """Status bar displaying HUD modules across left/center/right zones."""

    DEFAULT_CSS = """
    HudBar {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text;
    }
    HudBar .hud-left { width: 1fr; }
    HudBar .hud-center { width: 1fr; content-align: center middle; }
    HudBar .hud-right { width: 1fr; content-align: right middle; }
    """

    def compose(self) -> ComposeResult:
        yield Label("", id="hud-left", classes="hud-left")
        yield Label("", id="hud-center", classes="hud-center")
        yield Label("", id="hud-right", classes="hud-right")

    def set_modules(self, modules: List[HudModule]) -> None:
        left = []
        center = []
        right = []
        for m in modules:
            text = f" {m.label}: {m.value} "
            if m.position == "left":
                left.append(text)
            elif m.position == "center":
                center.append(text)
            else:
                right.append(text)
        try:
            self.query_one("#hud-left", Label).update("│".join(left))
            self.query_one("#hud-center", Label).update("│".join(center))
            self.query_one("#hud-right", Label).update("│".join(right))
        except NoMatches:
            pass


# ── Menu Overlay ─────────────────────────────────────────────────────────────


class MenuOverlay(Container):
    """Floating menu overlay using OptionList."""

    DEFAULT_CSS = """
    MenuOverlay {
        align: center middle;
        width: 60;
        height: 20;
        border: round $accent;
        background: $surface;
        layer: overlay;
    }
    MenuOverlay OptionList {
        width: 100%;
        height: 1fr;
    }
    MenuOverlay .menu-prompt {
        height: 1;
        background: $accent;
        color: $text;
        text-align: center;
    }
    """

    def __init__(
        self,
        items: List[MenuItem],
        prompt: str = "Select:",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._items = items
        self._prompt = prompt
        self._result: Optional[str] = None
        self._event: asyncio.Event = asyncio.Event()

    def compose(self) -> ComposeResult:
        yield Label(self._prompt, classes="menu-prompt")
        option_list = OptionList(id="menu-options")
        for item in self._items:
            prefix = "  " * item.depth
            icon = f"{item.icon} " if item.icon else ""
            label = f"{prefix}{icon}{item.label}"
            if item.description:
                label += f"  ({item.description})"
            option_list.add_option(Option(label, id=item.id))
        yield option_list

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self._result = event.option.id
        self._event.set()
        self.remove()

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self._result = None
            self._event.set()
            self.remove()

    async def wait_for_result(self) -> Optional[str]:
        await self._event.wait()
        return self._result


# ── Tab Bar Widget ───────────────────────────────────────────────────────────


class TabBar(Horizontal):
    """Displays tab stack indicators for each pane."""

    DEFAULT_CSS = """
    TabBar {
        height: 1;
        dock: top;
        background: $surface-darken-1;
    }
    TabBar .tab-item {
        padding: 0 1;
    }
    TabBar .tab-item.active {
        background: $accent;
        text-style: bold;
    }
    """

    def update_tabs(self, pane_handles: List[str], focused: Optional[str]) -> None:
        self.remove_children()
        for handle in pane_handles:
            classes = "tab-item active" if handle == focused else "tab-item"
            self.mount(Label(f" {handle[-6:]} ", classes=classes))


# ── NexusApp ─────────────────────────────────────────────────────────────────


class NexusApp(App):
    """The Textual application that IS the TextualSurface display.

    All pane management, menu rendering, HUD display, and notifications
    go through this App instance.
    """

    CSS = """
    #workspace {
        width: 100%;
        height: 1fr;
    }
    #pane-grid {
        width: 100%;
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("alt+m", "open_menu", "Menu", show=True),
        Binding("alt+h", "focus_left", "Focus Left"),
        Binding("alt+l", "focus_right", "Focus Right"),
        Binding("alt+j", "focus_down", "Focus Down"),
        Binding("alt+k", "focus_up", "Focus Up"),
        Binding("alt+q", "quit", "Quit"),
    ]

    session_name: reactive[str] = reactive("")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.panes: Dict[str, PaneState] = {}
        self._pane_counter = 0
        self._focused_handle: Optional[str] = None
        self._session: Optional[str] = None
        self._env: Dict[str, str] = {}
        self._hud_modules: List[HudModule] = []
        self._menu_future: Optional[asyncio.Future] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield TabBar(id="tab-bar")
        yield Vertical(id="workspace")
        yield HudBar(id="hud-bar")
        yield Footer()

    # -- Pane Management (called by TextualSurface) ---------------------------

    def add_pane(
        self,
        command: str = "",
        cwd: str = "",
    ) -> str:
        """Create a new pane, returning its handle."""
        self._pane_counter += 1
        handle = f"pane-{self._pane_counter}"
        state = PaneState(
            handle=handle,
            index=self._pane_counter,
            command=command or os.environ.get("SHELL", "/bin/sh"),
            title=command or "shell",
        )
        self.panes[handle] = state

        widget = PtyPane(state, id=handle)
        try:
            grid = self.query_one("#workspace")
            grid.mount(widget)
        except NoMatches:
            pass

        if self._focused_handle is None:
            self._focused_handle = handle
            state.focused = True

        self._refresh_tab_bar()
        return handle

    def split_pane(
        self,
        handle: str,
        direction: SplitDirection,
        size: Optional[int] = None,
        cwd: str = "",
    ) -> str:
        """Split an existing pane, creating a new sibling."""
        # For now: just add a new pane next to the target
        # Full CSS-grid splitting is a future enhancement
        return self.add_pane(cwd=cwd)

    def remove_pane(self, handle: str) -> None:
        """Destroy a pane and its PTY process."""
        if handle not in self.panes:
            return
        try:
            widget = self.query_one(f"#{handle}", PtyPane)
            widget.cleanup()
            widget.remove()
        except NoMatches:
            pass
        del self.panes[handle]

        if self._focused_handle == handle:
            self._focused_handle = next(iter(self.panes), None)

        self._refresh_tab_bar()

    def focus_pane(self, handle: str) -> None:
        """Move focus to a specific pane."""
        if handle not in self.panes:
            return
        # Unfocus old
        if self._focused_handle and self._focused_handle in self.panes:
            self.panes[self._focused_handle].focused = False
            try:
                old = self.query_one(f"#{self._focused_handle}", PtyPane)
                old.remove_class("focused")
            except NoMatches:
                pass

        # Focus new
        self._focused_handle = handle
        self.panes[handle].focused = True
        try:
            widget = self.query_one(f"#{handle}", PtyPane)
            widget.add_class("focused")
            widget.focus()
        except NoMatches:
            pass
        self._refresh_tab_bar()

    def _refresh_tab_bar(self) -> None:
        try:
            tab_bar = self.query_one("#tab-bar", TabBar)
            tab_bar.update_tabs(list(self.panes.keys()), self._focused_handle)
        except NoMatches:
            pass

    # -- Menu ----------------------------------------------------------------

    async def show_menu_async(
        self, items: List[MenuItem], prompt: str = "Select:"
    ) -> Optional[str]:
        overlay = MenuOverlay(items, prompt, id="menu-overlay")
        await self.mount(overlay)
        return await overlay.wait_for_result()

    # -- HUD -----------------------------------------------------------------

    def update_hud(self, modules: List[HudModule]) -> None:
        self._hud_modules = modules
        try:
            hud = self.query_one("#hud-bar", HudBar)
            hud.set_modules(modules)
        except NoMatches:
            pass

    # -- Actions (keybind handlers) ------------------------------------------

    def action_focus_left(self) -> None:
        self._focus_adjacent(-1)

    def action_focus_right(self) -> None:
        self._focus_adjacent(1)

    def action_focus_down(self) -> None:
        self._focus_adjacent(1)

    def action_focus_up(self) -> None:
        self._focus_adjacent(-1)

    def _focus_adjacent(self, offset: int) -> None:
        handles = list(self.panes.keys())
        if not handles or self._focused_handle is None:
            return
        try:
            idx = handles.index(self._focused_handle)
        except ValueError:
            return
        new_idx = (idx + offset) % len(handles)
        self.focus_pane(handles[new_idx])

    def action_open_menu(self) -> None:
        self.notify("Menu not connected yet", severity="information")


# ── TextualSurface ───────────────────────────────────────────────────────────


class TextualSurface(Surface):
    """Concrete Surface implementation using Textual.

    Level 0 (contained): all panes are widget divisions inside one
    terminal window. No OS-level window management.

    Usage:
        surface = TextualSurface()
        core = NexusCore(surface)
        surface.run()  # blocks — starts the Textual event loop
    """

    def __init__(self) -> None:
        self._app: Optional[NexusApp] = None
        self._sessions: Dict[str, str] = {}  # session_handle -> session_name

    @property
    def app(self) -> NexusApp:
        if self._app is None:
            self._app = NexusApp()
        return self._app

    def run(self, **kwargs: Any) -> None:
        """Start the Textual app (blocking). Call after NexusCore setup."""
        self.app.run(**kwargs)

    async def run_async(self, **kwargs: Any) -> None:
        """Start the Textual app asynchronously."""
        await self.app.run_async(**kwargs)

    # -- Lifecycle -----------------------------------------------------------

    def initialize(self, session_name: str, cwd: str = "") -> str:
        handle = f"textual:{session_name}"
        self._sessions[handle] = session_name
        self.app.session_name = session_name
        self.app.title = f"Nexus — {session_name}"
        if cwd:
            os.chdir(cwd)
        return handle

    def teardown(self, session: str) -> None:
        # Clean up all panes
        for handle in list(self.app.panes.keys()):
            self.app.remove_pane(handle)
        self._sessions.pop(session, None)

    # -- Spatial -------------------------------------------------------------

    def create_container(self, session: str, command: str = "",
                         cwd: str = "") -> str:
        return self.app.add_pane(command=command, cwd=cwd)

    def split(self, handle: str, direction: SplitDirection,
              size: Optional[int] = None, cwd: str = "") -> str:
        return self.app.split_pane(handle, direction, size, cwd)

    def destroy_container(self, handle: str) -> None:
        self.app.remove_pane(handle)

    def focus(self, handle: str) -> None:
        self.app.focus_pane(handle)

    def resize(self, handle: str, dimensions: Dimensions) -> None:
        state = self.app.panes.get(handle)
        if state is None:
            return
        state.width = dimensions.width
        state.height = dimensions.height
        # The actual widget will be resized by Textual's layout engine

    # -- Content -------------------------------------------------------------

    def attach_process(self, handle: str, command: str) -> None:
        state = self.app.panes.get(handle)
        if state is None:
            return
        # Kill existing process if any
        try:
            widget = self.app.query_one(f"#{handle}", PtyPane)
            widget.cleanup()
            state.command = command
            widget._spawn_process(command)
        except NoMatches:
            pass

    def send_input(self, handle: str, keys: str) -> None:
        state = self.app.panes.get(handle)
        if state is None or state.fd < 0:
            return
        try:
            os.write(state.fd, keys.encode("utf-8"))
        except OSError:
            pass

    # -- State ---------------------------------------------------------------

    def list_containers(self, session: str) -> List[ContainerInfo]:
        return [
            ContainerInfo(
                handle=s.handle,
                index=s.index,
                width=s.width,
                height=s.height,
                command=s.command,
                title=s.title,
                focused=s.focused,
                tags=dict(s.tags),
            )
            for s in self.app.panes.values()
        ]

    def get_focused(self, session: str) -> Optional[str]:
        return self.app._focused_handle

    def get_dimensions(self, handle: str) -> Dimensions:
        state = self.app.panes.get(handle)
        if state is None:
            return Dimensions(width=0, height=0)
        return Dimensions(width=state.width, height=state.height)

    def get_geometry(self, handle: str):
        state = self.app.panes.get(handle)
        if state is None:
            return None
        return {"x": 0, "y": 0, "w": state.width, "h": state.height}

    def set_geometry(self, handle: str, geometry: dict) -> None:
        state = self.app.panes.get(handle)
        if state:
            state.width = geometry.get("w", state.width)
            state.height = geometry.get("h", state.height)

    def swap_containers(self, source: str, target: str) -> bool:
        return source in self.app.panes and target in self.app.panes

    def container_exists(self, handle: str) -> bool:
        return handle in self.app.panes

    # -- Metadata ------------------------------------------------------------

    def set_tag(self, handle: str, key: str, value: str) -> None:
        state = self.app.panes.get(handle)
        if state:
            state.tags[key] = value

    def get_tag(self, handle: str, key: str) -> str:
        state = self.app.panes.get(handle)
        if state:
            return state.tags.get(key, "")
        return ""

    def set_title(self, handle: str, title: str) -> None:
        state = self.app.panes.get(handle)
        if state:
            state.title = title

    # -- Rendering -----------------------------------------------------------

    def show_menu(self, items: List[MenuItem],
                  prompt: str = "Select:") -> Optional[str]:
        # Synchronous wrapper — in practice menus will be async
        # For non-async callers, return None (menu requires event loop)
        if self._app and self._app.is_running:
            # Schedule async menu and block — only works from worker thread
            import concurrent.futures
            future: concurrent.futures.Future = concurrent.futures.Future()

            async def _show() -> None:
                result = await self.app.show_menu_async(items, prompt)
                future.set_result(result)

            self._app.call_from_thread(_show)
            try:
                return future.result(timeout=60)
            except Exception:
                return None
        return None

    def show_hud(self, modules: List[HudModule]) -> None:
        self.app.update_hud(modules)

    def notify(self, message: str, level: str = "info") -> None:
        severity = "information" if level == "info" else level
        if self._app and self._app.is_running:
            self._app.notify(message, severity=severity)

    # -- Layout --------------------------------------------------------------

    def apply_layout(self, session: str, layout: dict) -> bool:
        """Apply a composition layout.

        Layout format:
            {"panes": [{"command": "nvim", "size": 60}, {"command": "zsh"}]}

        Returns True on success.
        """
        panes = layout.get("panes", [])
        if not panes:
            return False

        # Clear existing panes
        for handle in list(self.app.panes.keys()):
            self.app.remove_pane(handle)

        # Create new panes from layout
        for pane_def in panes:
            cmd = pane_def.get("command", "")
            cwd = pane_def.get("cwd", "")
            self.app.add_pane(command=cmd, cwd=cwd)

        return True

    def capture_layout(self, session: str) -> dict:
        """Capture current layout for persistence."""
        panes = []
        for state in self.app.panes.values():
            panes.append({
                "handle": state.handle,
                "command": state.command,
                "title": state.title,
                "width": state.width,
                "height": state.height,
                "tags": dict(state.tags),
            })
        return {"panes": panes, "focused": self.app._focused_handle}

    # -- Environment ---------------------------------------------------------

    def set_env(self, session: str, key: str, value: str) -> None:
        self.app._env[key] = value
        os.environ[key] = value
