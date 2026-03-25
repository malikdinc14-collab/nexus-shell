#!/usr/bin/env python3
"""
Adapter Resolver
================
Singleton factory that provides the correct adapter instances based on
the current environment. All action modules use this to get adapters
instead of constructing them directly.

INVARIANT: This is the ONLY place where adapter construction decisions
are made. If you're instantiating an adapter elsewhere, you're doing
it wrong.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Ensure engine is importable
_ENGINE_ROOT = Path(__file__).resolve().parents[2]
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from engine.capabilities.base import MultiplexerCapability, EditorCapability


class AdapterResolver:
    """Resolves and caches adapter instances for the current session."""

    _multiplexer: Optional[MultiplexerCapability] = None
    _editor: Optional[EditorCapability] = None

    @classmethod
    def multiplexer(cls) -> MultiplexerCapability:
        """Returns the active MultiplexerCapability adapter."""
        if cls._multiplexer is None:
            cls._multiplexer = cls._resolve_multiplexer()
        return cls._multiplexer

    @classmethod
    def editor(cls) -> EditorCapability:
        """Returns the active EditorCapability adapter."""
        if cls._editor is None:
            cls._editor = cls._resolve_editor()
        return cls._editor

    @classmethod
    def reset(cls):
        """Clears cached adapters (for testing)."""
        cls._multiplexer = None
        cls._editor = None

    @classmethod
    def _resolve_multiplexer(cls) -> MultiplexerCapability:
        if os.environ.get("NEXUS_SIMULATION") == "1":
            from engine.capabilities.adapters.multiplexer.null import NullAdapter
            return NullAdapter()

        socket_label = os.environ.get("SOCKET_LABEL", "")

        # Auto-detect nexus socket if not in env
        if not socket_label and not os.environ.get("TMUX"):
            try:
                import glob as _glob
                sockets = _glob.glob("/tmp/tmux-*/nexus_*")
                if sockets:
                    socket_label = Path(sockets[0]).name
            except Exception:
                pass

        from engine.capabilities.adapters.multiplexer.tmux import TmuxAdapter
        return TmuxAdapter(socket_label=socket_label)

    @classmethod
    def _resolve_editor(cls) -> EditorCapability:
        from engine.capabilities.adapters.editor.neovim import NeovimAdapter
        return NeovimAdapter()
