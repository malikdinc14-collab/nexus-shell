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

class CapabilityType(Enum):
    EDITOR = auto()
    EXPLORER = auto()
    EXECUTOR = auto()
    AGENT = auto()
    RENDERER = auto()
    CHAT = auto()

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
