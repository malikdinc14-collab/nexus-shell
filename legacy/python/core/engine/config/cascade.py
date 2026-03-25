"""
Scope cascade resolver for nexus-shell configuration.

Resolution order (first non-None wins):
  1. Workspace  — .nexus/<file>
  2. Profile    — ~/.config/nexus/profiles/<name>/<file>
  3. Global     — ~/.config/nexus/<file>

Reads YAML files and resolves individual keys or whole documents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass(frozen=True)
class CascadeResolver:
    """Resolve configuration values through the workspace > profile > global cascade."""

    global_dir: Path
    workspace_dir: Path
    profile: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, filename: str, key: Optional[str] = None) -> Any:
        """Return the resolved value for *key* inside *filename*.

        If *key* is None, return the merged document (workspace keys
        override profile keys override global keys).

        Returns None when no file or key is found at any layer.
        """
        if key is not None:
            return self._resolve_key(filename, key)
        return self._resolve_document(filename)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _layer_dirs(self) -> list[Path]:
        """Return directories in cascade priority order (highest first)."""
        layers: list[Path] = [self.workspace_dir]
        if self.profile:
            layers.append(self.global_dir / "profiles" / self.profile)
        layers.append(self.global_dir)
        return layers

    def _read_yaml(self, path: Path) -> Optional[dict]:
        """Safely read a YAML file. Returns None on missing/empty/broken files."""
        if not path.is_file():
            return None
        try:
            data = yaml.safe_load(path.read_text())
            return data if isinstance(data, dict) else None
        except yaml.YAMLError:
            return None

    def _resolve_key(self, filename: str, key: str) -> Any:
        """Walk layers top-down, return first non-None value for *key*."""
        for layer_dir in self._layer_dirs():
            data = self._read_yaml(layer_dir / filename)
            if data is not None and key in data:
                return data[key]
        return None

    def _resolve_document(self, filename: str) -> Optional[dict]:
        """Merge all layers bottom-up so higher layers override lower ones."""
        merged: dict = {}
        # Walk in reverse (global first) so workspace overwrites last.
        for layer_dir in reversed(self._layer_dirs()):
            data = self._read_yaml(layer_dir / filename)
            if data is not None:
                merged.update(data)
        return merged if merged else None
