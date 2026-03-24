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
import select
import signal
import struct
import termios
import threading
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

# ── PTY Color Map ────────────────────────────────────────────────────────────

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


# ── Data Models ──────────────────────────────────────────────────────────────


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


@dataclass
class SplitNode:
    """Binary tree node for spatial layout.

    Leaf nodes have pane_handle set.
    Branch nodes have direction + first/second children.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    direction: Optional[SplitDirection] = None  # None = leaf
    ratio: float = 0.5
    first: Optional[SplitNode] = None
    second: Optional[SplitNode] = None
    pane_handle: Optional[str] = None  # leaf only

    @property
    def is_leaf(self) -> bool:
        return self.direction is None

    def find_leaf(self, handle: str) -> Optional[SplitNode]:
        """Find the leaf node with the given pane handle."""
        if self.is_leaf:
            return self if self.pane_handle == handle else None
        if self.first:
            result = self.first.find_leaf(handle)
            if result:
                return result
        if self.second:
            return self.second.find_leaf(handle)
        return None

    def find_parent(self, handle: str) -> Optional[SplitNode]:
        """Find the parent of the leaf with the given handle."""
        if self.is_leaf:
            return None
        for child in (self.first, self.second):
            if child and child.is_leaf and child.pane_handle == handle:
                return self
            if child:
                result = child.find_parent(handle)
                if result:
                    return result
        return None

    def all_handles(self) -> List[str]:
        """Collect all pane handles from leaf nodes."""
        if self.is_leaf:
            return [self.pane_handle] if self.pane_handle else []
        handles = []
        if self.first:
            handles.extend(self.first.all_handles())
        if self.second:
            handles.extend(self.second.all_handles())
        return handles


# ── PTY Pane Widget ──────────────────────────────────────────────────────────


class PtyPane(Static):
    """A widget that hosts a PTY-backed terminal process.

    Uses pyte to emulate a VT100 terminal and renders the screen buffer
    as Rich text on each update cycle.

    Handles re-mounting gracefully: if the PaneState already has a running
    PTY (fd >= 0), the widget picks it up without respawning.
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
        self._stop = threading.Event()

    def on_mount(self) -> None:
        self._stop.clear()
        if self.pane_state.fd >= 0:
            # Re-mount: pick up existing PTY, render current buffer
            self._render_screen()
            self._start_reader()
        elif self.pane_state.command:
            self._spawn_process(self.pane_state.command)

    def on_unmount(self) -> None:
        self._stop.set()

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
        """Read PTY output in a background thread and feed to pyte.

        Uses select() with a short timeout so the thread exits cleanly
        when the widget is unmounted (stop event is set).
        """
        state = self.pane_state
        fd = state.fd
        while not self._stop.is_set():
            try:
                ready, _, _ = select.select([fd], [], [], 0.05)
                if not ready:
                    continue
                data = os.read(fd, 4096)
                if not data:
                    break
                state.stream.feed(data.decode("utf-8", errors="replace"))
                self.app.call_from_thread(self._render_screen)
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
        self._stop.set()
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
            self.query_one("#hud-left", Label).update("|".join(left))
            self.query_one("#hud-center", Label).update("|".join(center))
            self.query_one("#hud-right", Label).update("|".join(right))
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
    """Displays pane indicators with stack identity labels."""

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

    def update_tabs(
        self,
        pane_handles: List[str],
        focused: Optional[str],
        panes: Optional[Dict[str, PaneState]] = None,
    ) -> None:
        self.remove_children()
        for handle in pane_handles:
            # Show stack_id tag if available, else truncated handle
            label = handle[-6:]
            if panes and handle in panes:
                sid = panes[handle].tags.get("nexus_stack_id", "")
                if sid:
                    label = sid
                elif panes[handle].title:
                    label = panes[handle].title[:10]
            classes = "tab-item active" if handle == focused else "tab-item"
            self.mount(Label(f" {label} ", classes=classes))


# ── NexusApp ─────────────────────────────────────────────────────────────────


class NexusApp(App):
    """The Textual application that IS the TextualSurface display.

    Manages a binary split tree for spatial layout. Each leaf in the tree
    holds a PtyPane widget. Splits create new branches; swap exchanges
    content between two leaves.
    """

    CSS = """
    #workspace {
        width: 100%;
        height: 1fr;
    }
    .split-h {
        width: 100%;
        height: 100%;
    }
    .split-v {
        width: 100%;
        height: 100%;
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
        self._split_root: Optional[SplitNode] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield TabBar(id="tab-bar")
        yield Vertical(id="workspace")
        yield HudBar(id="hud-bar")
        yield Footer()

    # -- Pane State Creation ---------------------------------------------------

    def _new_handle(self) -> str:
        self._pane_counter += 1
        return f"pane-{self._pane_counter}"

    def _create_pane_state(
        self, command: str = "", cwd: str = ""
    ) -> PaneState:
        """Create a PaneState (no widget yet)."""
        handle = self._new_handle()
        state = PaneState(
            handle=handle,
            index=self._pane_counter,
            command=command or os.environ.get("SHELL", "/bin/sh"),
            title=command or "shell",
        )
        self.panes[handle] = state
        return state

    # -- Split Tree → Widget Tree Rendering ------------------------------------

    def _build_widget_tree(self, node: SplitNode) -> Widget:
        """Recursively build a Textual widget tree from the split tree."""
        if node.is_leaf:
            state = self.panes.get(node.pane_handle)
            if state:
                return PtyPane(state, id=node.pane_handle)
            return Static("(empty)", id=f"empty-{node.id}")

        first_widget = self._build_widget_tree(node.first)
        second_widget = self._build_widget_tree(node.second)

        if node.direction == SplitDirection.HORIZONTAL:
            pct = int(node.ratio * 100)
            first_widget.styles.width = f"{pct}%"
            second_widget.styles.width = f"{100 - pct}%"
            first_widget.styles.height = "100%"
            second_widget.styles.height = "100%"
            return Horizontal(
                first_widget, second_widget,
                id=f"split-{node.id}", classes="split-h",
            )
        else:
            pct = int(node.ratio * 100)
            first_widget.styles.height = f"{pct}%"
            second_widget.styles.height = f"{100 - pct}%"
            first_widget.styles.width = "100%"
            second_widget.styles.width = "100%"
            return Vertical(
                first_widget, second_widget,
                id=f"split-{node.id}", classes="split-v",
            )

    async def _rebuild_workspace(self) -> None:
        """Clear workspace and rebuild widget tree from split tree.

        PaneStates survive — only widgets are recreated. Existing PTY
        processes are picked up by new PtyPane instances via on_mount.
        """
        try:
            workspace = self.query_one("#workspace")
        except NoMatches:
            return

        # Cleanup existing PtyPane widgets (stop readers, but keep PTY alive)
        for widget in self.query(PtyPane):
            widget._stop.set()
        await workspace.remove_children()

        if self._split_root:
            tree = self._build_widget_tree(self._split_root)
            await workspace.mount(tree)

        self._refresh_tab_bar()

    # -- Pane Management (called by TextualSurface) ----------------------------

    def add_pane(self, command: str = "", cwd: str = "") -> str:
        """Create a new pane and add it to the layout.

        First pane becomes the root leaf. Subsequent panes split the
        focused pane horizontally.
        """
        state = self._create_pane_state(command, cwd)
        handle = state.handle

        if self._split_root is None:
            # First pane — root leaf
            self._split_root = SplitNode(pane_handle=handle)
        else:
            # Add by splitting the focused pane (or root)
            target = self._focused_handle
            if target and self._split_root.find_leaf(target):
                self._split_at(target, handle, SplitDirection.HORIZONTAL)
            else:
                # Split the first leaf we find
                handles = self._split_root.all_handles()
                if handles:
                    self._split_at(handles[0], handle, SplitDirection.HORIZONTAL)

        if self._focused_handle is None:
            self._focused_handle = handle
            state.focused = True

        # Schedule rebuild (works both during and after compose)
        self.call_later(self._rebuild_workspace)
        return handle

    def _split_at(
        self,
        target_handle: str,
        new_handle: str,
        direction: SplitDirection,
        ratio: float = 0.5,
    ) -> None:
        """Split the leaf at target_handle, placing new_handle as sibling.

        Mutates the split tree in-place by replacing the target leaf with
        a branch containing both the old and new leaf.
        """
        if self._split_root is None:
            return

        if self._split_root.is_leaf and self._split_root.pane_handle == target_handle:
            # Root is the target — wrap it
            old_root = SplitNode(
                pane_handle=target_handle,
                id=self._split_root.id,
            )
            self._split_root = SplitNode(
                direction=direction,
                ratio=ratio,
                first=old_root,
                second=SplitNode(pane_handle=new_handle),
            )
            return

        parent = self._split_root.find_parent(target_handle)
        if not parent:
            return

        # Replace the leaf child with a branch
        for attr in ("first", "second"):
            child = getattr(parent, attr)
            if child and child.is_leaf and child.pane_handle == target_handle:
                new_branch = SplitNode(
                    direction=direction,
                    ratio=ratio,
                    first=SplitNode(pane_handle=target_handle, id=child.id),
                    second=SplitNode(pane_handle=new_handle),
                )
                setattr(parent, attr, new_branch)
                return

    def split_pane(
        self,
        handle: str,
        direction: SplitDirection,
        size: Optional[int] = None,
        cwd: str = "",
    ) -> str:
        """Split an existing pane, creating a new sibling."""
        if handle not in self.panes:
            return ""
        state = self._create_pane_state(cwd=cwd)
        ratio = (size / 100) if size else 0.5
        self._split_at(handle, state.handle, direction, ratio)
        self.call_later(self._rebuild_workspace)
        return state.handle

    def remove_pane(self, handle: str) -> None:
        """Destroy a pane and its PTY process, pruning the split tree."""
        if handle not in self.panes:
            return

        # Cleanup widget
        try:
            widget = self.query_one(f"#{handle}", PtyPane)
            widget.cleanup()
        except NoMatches:
            pass

        # Prune the split tree
        if self._split_root:
            if self._split_root.is_leaf and self._split_root.pane_handle == handle:
                self._split_root = None
            else:
                parent = self._split_root.find_parent(handle)
                if parent:
                    # Replace parent with the surviving sibling
                    survivor = None
                    if parent.first and parent.first.is_leaf and parent.first.pane_handle == handle:
                        survivor = parent.second
                    elif parent.second and parent.second.is_leaf and parent.second.pane_handle == handle:
                        survivor = parent.first

                    if survivor:
                        # Check if parent is root
                        if parent is self._split_root:
                            self._split_root = survivor
                        else:
                            grandparent = self._split_root.find_parent(
                                parent.first.pane_handle if parent.first and parent.first.is_leaf
                                else parent.first.all_handles()[0] if parent.first
                                else handle
                            )
                            # Simpler: just rebuild since tree mutation is complex
                            # The find_parent doesn't find by node ID, so just do it
                            pass

        del self.panes[handle]

        if self._focused_handle == handle:
            self._focused_handle = next(iter(self.panes), None)

        self.call_later(self._rebuild_workspace)

    def swap_panes(self, source: str, target: str) -> bool:
        """Swap two panes by exchanging their positions in the split tree.

        The PTY processes stay attached to their PaneStates — only the
        tree leaf handles are swapped, so each pane appears where the
        other was.
        """
        if not self._split_root:
            return False

        source_leaf = self._split_root.find_leaf(source)
        target_leaf = self._split_root.find_leaf(target)

        if source_leaf and target_leaf:
            # Both visible: swap positions in tree
            source_leaf.pane_handle = target
            target_leaf.pane_handle = source
            self.call_later(self._rebuild_workspace)
            return True

        # One or both not in tree — still valid for NexusCore
        # (background panes exist in panes dict but not in split tree)
        if source in self.panes and target in self.panes:
            if source_leaf:
                source_leaf.pane_handle = target
                self.call_later(self._rebuild_workspace)
            elif target_leaf:
                target_leaf.pane_handle = source
                self.call_later(self._rebuild_workspace)
            return True

        return False

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
            handles = (
                self._split_root.all_handles() if self._split_root else []
            )
            tab_bar.update_tabs(handles, self._focused_handle, self.panes)
        except NoMatches:
            pass

    # -- Composition Loading ---------------------------------------------------

    async def load_composition(self, layout: dict) -> None:
        """Build a split tree from a composition layout dict.

        Format (from vscodelike.json etc.):
            {"type": "hsplit", "panes": [
                {"id": "files", "size": 30, "command": "..."},
                {"type": "vsplit", "panes": [...]},
            ]}
        """
        # Cleanup existing panes
        for handle in list(self.panes.keys()):
            self.remove_pane(handle)

        self._split_root = self._parse_layout_node(layout)
        await self._rebuild_workspace()

        # Focus the first pane
        if self._split_root:
            handles = self._split_root.all_handles()
            if handles:
                self._focused_handle = handles[0]
                self.panes[handles[0]].focused = True
                self._refresh_tab_bar()

    def _parse_layout_node(self, node: dict) -> SplitNode:
        """Recursively parse a composition layout dict into a SplitNode tree."""
        split_type = node.get("type")

        if split_type in ("hsplit", "vsplit"):
            direction = (
                SplitDirection.HORIZONTAL
                if split_type == "hsplit"
                else SplitDirection.VERTICAL
            )
            children = node.get("panes", [])
            if len(children) < 2:
                # Single child — just return it as leaf
                if children:
                    return self._parse_layout_node(children[0])
                return SplitNode()

            # Build binary tree from N children
            # Compute ratios from sizes: sized children get their share,
            # unsized children split the remainder equally
            return self._build_nary_split(children, direction)

        # Leaf node (a pane)
        command = node.get("command", "")
        state = self._create_pane_state(command=command)
        pane_id = node.get("id", "")
        if pane_id:
            state.tags["nexus_stack_id"] = pane_id
            state.title = pane_id
        return SplitNode(pane_handle=state.handle)

    def _build_nary_split(
        self, children: List[dict], direction: SplitDirection
    ) -> SplitNode:
        """Convert N children into a binary split tree.

        Sizes are percentages. Unsized children split the remainder
        equally: remainder = 100 - sum(explicit sizes).
        """
        # Resolve all sizes first so unsized nodes get fair remainder
        resolved = self._resolve_sizes(children)

        if len(children) == 1:
            return self._parse_layout_node(children[0])

        if len(children) == 2:
            first = self._parse_layout_node(children[0])
            second = self._parse_layout_node(children[1])
            s1, s2 = resolved[0], resolved[1]
            ratio = s1 / (s1 + s2) if (s1 + s2) > 0 else 0.5
            return SplitNode(
                direction=direction, ratio=ratio,
                first=first, second=second,
            )

        # N > 2: split first child vs rest
        first = self._parse_layout_node(children[0])
        rest = self._build_nary_split(children[1:], direction)
        s_first = resolved[0]
        s_rest = sum(resolved[1:])
        ratio = s_first / (s_first + s_rest) if (s_first + s_rest) > 0 else 0.5
        return SplitNode(
            direction=direction, ratio=ratio,
            first=first, second=rest,
        )

    @staticmethod
    def _resolve_sizes(children: List[dict]) -> List[float]:
        """Resolve sizes for a list of layout children.

        Explicit sizes are kept as-is. Unsized children split the
        remainder (100 - sum_of_explicit) equally.
        """
        explicit_total = 0.0
        unsized_count = 0
        sizes: List[Optional[float]] = []

        for child in children:
            raw = child.get("size")
            if raw is not None:
                try:
                    val = float(raw)
                    sizes.append(val)
                    explicit_total += val
                    continue
                except (TypeError, ValueError):
                    pass
            sizes.append(None)
            unsized_count += 1

        # Distribute remainder to unsized children
        remainder = max(100.0 - explicit_total, 10.0)
        fair_share = remainder / unsized_count if unsized_count > 0 else 30.0

        return [s if s is not None else fair_share for s in sizes]

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
        if not self._split_root:
            return
        handles = self._split_root.all_handles()
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

    # -- Swap ----------------------------------------------------------------

    def swap_containers(self, source: str, target: str) -> bool:
        return self.app.swap_panes(source, target)

    def container_exists(self, handle: str) -> bool:
        return handle in self.app.panes

    # -- Content -------------------------------------------------------------

    def attach_process(self, handle: str, command: str) -> None:
        state = self.app.panes.get(handle)
        if state is None:
            return
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
        if self._app and self._app.is_running:
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

        Accepts either the full composition JSON or just the layout dict:
            {"type": "hsplit", "panes": [...]}
        """
        # Handle full composition format vs bare layout
        target = layout.get("layout", layout)
        if not target.get("panes") and not target.get("type"):
            return False

        if self._app and self._app.is_running:
            self._app.call_from_thread(
                lambda: self.app.load_composition(target)
            )
        else:
            # Pre-run: schedule for when app starts
            async def _load() -> None:
                await self.app.load_composition(target)
            self.app.call_later(_load)
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
