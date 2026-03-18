#!/usr/bin/env python3
# core/engine/capabilities/base.py
"""
Nexus Capability Model (V3)
==========================
Abstract Base Classes for system-level capabilities.
Capabilities represent 'What' can be done, regardless of 'How'.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from enum import Enum, auto
from dataclasses import dataclass, field


@dataclass
class PaneInfo:
    """
    Backend-agnostic descriptor for a single pane/split/window.
    MultiplexerAdapters return this from list_panes() so the
    orchestrator never touches raw tmux format strings.
    """
    handle: str          # Backend-specific ID (e.g. '%5', 'pane:0x1')
    index: int           # Position within parent window (0-based)
    width: int
    height: int
    x: int = 0
    y: int = 0
    stack_id: str = ""   # @nexus_stack_id value
    role: str = ""       # @nexus_role value (legacy, optional)
    command: str = ""    # Foreground process name
    tags: Dict[str, str] = field(default_factory=dict)


class CapabilityType(Enum):
    EDITOR = auto()
    EXPLORER = auto()
    EXECUTOR = auto()
    AGENT = auto()
    RENDERER = auto()
    CHAT = auto()
    MENU = auto()
    MULTIPLEXER = auto()   # ← NEW: terminal multiplexer backends


class Capability(ABC):
    """Base class for all system capabilities."""
    
    @property
    @abstractmethod
    def capability_type(self) -> CapabilityType:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the underlying tool/adapter is ready."""
        pass

class EditorCapability(Capability):
    """Abstract interface for text editing operations."""
    
    @property
    def capability_type(self): return CapabilityType.EDITOR

    @abstractmethod
    def open_resource(self, path: str, line: int = 1, column: int = 1) -> bool:
        """Opens a file at a specific location."""
        pass

    @abstractmethod
    def get_current_buffer(self) -> Optional[str]:
        """Returns the path of the currently active file."""
        pass

    @abstractmethod
    def apply_edit(self, patch: str) -> bool:
        """Applies a patch or substitution to the current buffer."""
        pass

class ExplorerCapability(Capability):
    """Abstract interface for file system navigation."""
    
    @property
    def capability_type(self): return CapabilityType.EXPLORER

    @abstractmethod
    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """Lists contents of a directory with metadata."""
        pass

    @abstractmethod
    def get_selection(self) -> Optional[str]:
        """Returns the currently highlighted item path."""
        pass

    @abstractmethod
    def trigger_action(self, action: str, payload: Any) -> bool:
        """Triggers a tool-specific action (e.g., 'yank', 'delete')."""
        pass

class ExecutorCapability(Capability):
    """Abstract interface for process execution and monitoring."""
    
    @property
    def capability_type(self): return CapabilityType.EXECUTOR

    @abstractmethod
    def spawn(self, command: str, cwd: str = None, env: Dict[str, str] = None) -> str:
        """Spawns a process and returns a handle/ID."""
        pass

    @abstractmethod
    def kill(self, handle: str) -> bool:
        """Terminates a running process."""
        pass

    @abstractmethod
    def get_status(self, handle: str) -> Dict[str, Any]:
        """Returns process stats (PID, CPU, Memory, Status)."""
        pass

class ChatCapability(Capability):
    """Abstract interface for AI chat interactions."""
    
    @property
    def capability_type(self): return CapabilityType.CHAT

    @abstractmethod
    def send_message(self, message: str) -> str:
        """Sends a message to the AI and returns the response."""
        pass

    @abstractmethod
    def get_history(self) -> List[Dict[str, str]]:
        """Returns the conversation history."""
        pass


class MenuCapability(Capability):
    """Abstract interface for interactive CLI menus."""
    
    @property
    def capability_type(self): return CapabilityType.MENU

    @abstractmethod
    def show_menu(self, options: List[str], prompt: str = "Select:") -> Optional[str]:
        """Displays a menu and returns the selected option."""
        pass


class MultiplexerCapability(Capability):
    """
    Abstract interface for terminal multiplexer backends.

    Invariants:
      - A session must exist before windows or panes can be created.
      - A window must exist before panes can be created within it.
      - Pane handles returned by split() are immediately valid.
      - Tags (set_tag / get_tag) are durable for the session lifetime.

    Implementations: TmuxAdapter, GhosttyAdapter, ITermAdapter, NullAdapter...
    """

    @property
    def capability_type(self): return CapabilityType.MULTIPLEXER

    # ── Session Management ──────────────────────────────────────────────────

    @abstractmethod
    def create_session(self, name: str, cwd: str = "",
                       width: int = 220, height: int = 50) -> str:
        """Creates a detached session. Returns session handle."""
        pass

    @abstractmethod
    def has_session(self, name: str) -> bool:
        """Returns True if a session with this name already exists."""
        pass

    @abstractmethod
    def attach(self, session: str, client_name: str = "") -> None:
        """Attaches a client to the given session."""
        pass

    @abstractmethod
    def kill_session(self, name: str) -> None:
        pass

    # ── Window Management ───────────────────────────────────────────────────

    @abstractmethod
    def create_window(self, session: str, name: str,
                      cwd: str = "") -> str:
        """Creates a new window. Returns window handle (e.g. 'session:index')."""
        pass

    @abstractmethod
    def list_windows(self, session: str) -> List[str]:
        """Returns list of window handles in a session."""
        pass

    # ── Pane Management ─────────────────────────────────────────────────────

    @abstractmethod
    def split(self, target: str, direction: str = "h",
              size: Optional[int] = None, cwd: str = "") -> str:
        """
        Splits a pane. direction: 'h' (horizontal) or 'v' (vertical).
        Returns the new pane handle.
        """
        pass

    @abstractmethod
    def kill_pane(self, handle: str) -> None:
        pass

    @abstractmethod
    def list_panes(self, window: str) -> List[PaneInfo]:
        """Returns all panes in a window as PaneInfo objects."""
        pass

    @abstractmethod
    def select_pane(self, handle: str) -> None:
        """Brings focus to a pane."""
        pass

    # ── Command Execution ───────────────────────────────────────────────────

    @abstractmethod
    def send_keys(self, handle: str, keys: str) -> None:
        """Sends a string as keystrokes to a pane (like typing)."""
        pass

    @abstractmethod
    def send_command(self, handle: str, cmd: str) -> None:
        """Sends a command + ENTER to a pane."""
        pass

    # ── Tag / Metadata ──────────────────────────────────────────────────────

    @abstractmethod
    def set_tag(self, handle: str, key: str, value: str) -> None:
        """Attaches arbitrary metadata to a pane (durable for session)."""
        pass

    @abstractmethod
    def get_tag(self, handle: str, key: str) -> str:
        """Retrieves metadata previously set with set_tag."""
        pass

    @abstractmethod
    def set_title(self, handle: str, title: str) -> None:
        """Sets the display title of the pane."""
        pass

    # ── Layout ──────────────────────────────────────────────────────────────

    @abstractmethod
    def apply_layout(self, window: str, layout: str) -> bool:
        """
        Applies a backend-specific layout descriptor.
        For tmux: a layout string. For others: a best-effort arrangement.
        Returns True on success.
        """
        pass

    @abstractmethod
    def get_dimensions(self, target: str) -> Dict[str, int]:
        """Returns {'width': N, 'height': N} for a window or pane."""
        pass

    # ── Environment ─────────────────────────────────────────────────────────

    @abstractmethod
    def set_env(self, session: str, key: str, value: str) -> None:
        """Sets an environment variable visible to all panes in the session."""
        pass
