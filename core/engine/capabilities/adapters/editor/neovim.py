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
from ...base import EditorCapability, AdapterManifest, CapabilityType

class NeovimAdapter(EditorCapability):
    # Neovim opens in TUI mode — needs attached terminal.
    STARTUP_DELAY_SECS: float = 0.3

    manifest = AdapterManifest(
        name="neovim",
        capability_type=CapabilityType.EDITOR,
        binary="nvim",
        binary_candidates=["nvim", "neovim"],
        native_multiplicity=True,
        priority=100,
    )

    def __init__(self, session_name: Optional[str] = None):
        import os
        self.nexus_state = Path(f"/tmp/nexus_{os.getlogin()}")
        self.session_name = session_name or self._get_tmux_session()
        self._bin = self._resolve_binary()

    def _resolve_binary(self):
        try:
            return subprocess.check_output(
                ["which", "nvim"], stderr=subprocess.DEVNULL
            ).decode().strip() or None
        except Exception:
            return None

    def get_launch_command(self, pipe: str = "") -> str:
        """Returns the best launch command for nvim, optionally with RPC pipe."""
        bin_path = self._bin or "nvim"
        cmd = f"sleep {self.STARTUP_DELAY_SECS} && {bin_path}"
        if pipe:
            cmd += f" --listen {pipe}"
        return cmd

    def _get_tmux_session(self):
        # Derive session name from env — no direct tmux calls in adapters
        # that aren't MultiplexerAdapters.
        return os.environ.get("NEXUS_SESSION", "nexus_default")

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
        pipe = self._get_pipe()
        if not pipe:
            return None
        try:
            result = subprocess.check_output(
                ["nvim", "--server", str(pipe), "--remote-expr", 'expand("%:p")'],
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).decode().strip()
            return result if result else None
        except Exception:
            return None

    def apply_edit(self, patch: str) -> bool:
        pipe = self._get_pipe()
        if not pipe:
            return False
        try:
            cmd = f":execute 'normal! i' . {repr(patch)}<CR>"
            subprocess.run(
                ["nvim", "--server", str(pipe), "--remote-send", cmd],
                check=True, stderr=subprocess.DEVNULL, timeout=2,
            )
            return True
        except Exception:
            return False

    def get_buffer_content(self, max_lines: int = 200) -> Optional[str]:
        pipe = self._get_pipe()
        if not pipe:
            return None
        try:
            expr = f'join(getline(1, {max_lines}), "\\n")'
            result = subprocess.check_output(
                ["nvim", "--server", str(pipe), "--remote-expr", expr],
                stderr=subprocess.DEVNULL, timeout=2,
            ).decode().strip()
            return result if result else None
        except Exception:
            return None

    def get_tabs(self) -> list:
        pipe = self._get_pipe()
        if not pipe:
            return []
        try:
            import json
            expr = 'json_encode(map(gettabinfo(), {k,v -> {"name": fnamemodify(bufname(v.windows[0]), ":t"), "index": v.tabnr}}))'
            result = subprocess.check_output(
                ["nvim", "--server", str(pipe), "--remote-expr", expr],
                stderr=subprocess.DEVNULL, timeout=2,
            ).decode().strip()
            return json.loads(result) if result else []
        except Exception:
            return []

    def remote_expr(self, expr: str) -> str:
        pipe = self._get_pipe()
        if not pipe:
            return ""
        try:
            result = subprocess.check_output(
                ["nvim", "--server", str(pipe), "--remote-expr", expr],
                stderr=subprocess.DEVNULL, timeout=2,
            ).decode().strip()
            return result or ""
        except Exception:
            return ""

    def send_editor_command(self, cmd: str) -> bool:
        pipe = self._get_pipe()
        if not pipe:
            return False
        try:
            subprocess.run(
                ["nvim", "--server", str(pipe), "--remote-send", cmd],
                check=True, stderr=subprocess.DEVNULL, timeout=2,
            )
            return True
        except Exception:
            return False
