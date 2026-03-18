#!/usr/bin/env python3
# core/engine/capabilities/adapters/neovim.py
"""
Neovim Capability Adapter (V3)
==============================
Maps EditorCapability interface to Neovim RPC/Socket commands.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional
from ..base import EditorCapability

class NeovimAdapter(EditorCapability):
    def __init__(self, session_name: str = None):
        self.nexus_state = Path(f"/tmp/nexus_{os.getuser()}")
        self.session_name = session_name or self._get_tmux_session()

    def _get_tmux_session(self):
        try:
            return subprocess.check_output(["tmux", "display-message", "-p", "#S"], stderr=subprocess.DEVNULL).decode().strip()
        except:
            return "nexus_default"

    def _get_pipe(self) -> Optional[Path]:
        project_name = self.session_name.replace("nexus_", "")
        pipe = self.nexus_state / f"pipes/nvim_{project_name}.pipe"
        return pipe if pipe.exists() else None

    def is_available(self) -> bool:
        return self._get_pipe() is not None

    def open_resource(self, path: str, line: int = 1, column: int = 1) -> bool:
        pipe = self._get_pipe()
        if not pipe: return False
        
        # Build Neovim command: :tabedit path | call cursor(line, col)
        cmd = f":tabedit {path}<CR>:call cursor({line}, {column})<CR>"
        
        try:
            subprocess.run(["nvim", "--server", str(pipe), "--remote-send", cmd], check=True)
            return True
        except:
            return False

    def get_current_buffer(self) -> Optional[str]:
        # Implementation would require --remote-expr or similar
        return None 

    def apply_edit(self, patch: str) -> bool:
        # Implementation through Neovim remote commands
        return False
