#!/usr/bin/env python3
# tests/unit/test_config_cascade.py
"""
Unit tests for the configuration cascade resolver and defaults system.

Covers:
  - T001: Config directory structure defaults (ensure_defaults)
  - T002: Scope cascade resolution (workspace > profile > global)

No live filesystem side-effects — all paths use tmp_path fixtures.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from engine.config.cascade import CascadeResolver
from engine.config.defaults import ensure_defaults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False))


# ---------------------------------------------------------------------------
# T002: CascadeResolver — scope precedence
# ---------------------------------------------------------------------------

class TestCascadeResolver:
    """Workspace > active profile > global. First non-None wins."""

    def test_global_value_returned_when_alone(self, tmp_path: Path):
        global_dir = tmp_path / "global"
        _write_yaml(global_dir / "adapters.yaml", {"editor": "neovim"})

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=tmp_path / "ws_empty",  # does not exist
        )
        assert resolver.get("adapters.yaml", "editor") == "neovim"

    def test_workspace_overrides_global(self, tmp_path: Path):
        global_dir = tmp_path / "global"
        ws_dir = tmp_path / "workspace" / ".nexus"

        _write_yaml(global_dir / "adapters.yaml", {"editor": "neovim"})
        _write_yaml(ws_dir / "adapters.yaml", {"editor": "helix"})

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=ws_dir,
        )
        assert resolver.get("adapters.yaml", "editor") == "helix"

    def test_profile_overrides_global(self, tmp_path: Path):
        global_dir = tmp_path / "global"
        profile_dir = global_dir / "profiles" / "work"

        _write_yaml(global_dir / "adapters.yaml", {"editor": "neovim"})
        _write_yaml(profile_dir / "adapters.yaml", {"editor": "vscode"})

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=tmp_path / "ws_empty",
            profile="work",
        )
        assert resolver.get("adapters.yaml", "editor") == "vscode"

    def test_workspace_overrides_profile(self, tmp_path: Path):
        global_dir = tmp_path / "global"
        profile_dir = global_dir / "profiles" / "work"
        ws_dir = tmp_path / "workspace" / ".nexus"

        _write_yaml(global_dir / "adapters.yaml", {"editor": "neovim"})
        _write_yaml(profile_dir / "adapters.yaml", {"editor": "vscode"})
        _write_yaml(ws_dir / "adapters.yaml", {"editor": "helix"})

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=ws_dir,
            profile="work",
        )
        assert resolver.get("adapters.yaml", "editor") == "helix"

    def test_full_cascade_order(self, tmp_path: Path):
        """Workspace wins over profile wins over global."""
        global_dir = tmp_path / "global"
        profile_dir = global_dir / "profiles" / "dev"
        ws_dir = tmp_path / "ws" / ".nexus"

        _write_yaml(global_dir / "adapters.yaml", {
            "editor": "neovim", "explorer": "yazi", "chat": "opencode",
        })
        _write_yaml(profile_dir / "adapters.yaml", {
            "editor": "vscode", "explorer": "ranger",
        })
        _write_yaml(ws_dir / "adapters.yaml", {
            "editor": "helix",
        })

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=ws_dir,
            profile="dev",
        )
        # workspace wins
        assert resolver.get("adapters.yaml", "editor") == "helix"
        # profile wins over global
        assert resolver.get("adapters.yaml", "explorer") == "ranger"
        # only global has this key
        assert resolver.get("adapters.yaml", "chat") == "opencode"

    def test_missing_file_returns_none(self, tmp_path: Path):
        resolver = CascadeResolver(
            global_dir=tmp_path / "nowhere",
            workspace_dir=tmp_path / "also_nowhere",
        )
        assert resolver.get("nonexistent.yaml", "key") is None

    def test_missing_key_returns_none(self, tmp_path: Path):
        global_dir = tmp_path / "global"
        _write_yaml(global_dir / "adapters.yaml", {"editor": "neovim"})

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=tmp_path / "ws_empty",
        )
        assert resolver.get("adapters.yaml", "nonexistent_key") is None

    def test_get_whole_file_without_key(self, tmp_path: Path):
        global_dir = tmp_path / "global"
        data = {"editor": "neovim", "explorer": "yazi"}
        _write_yaml(global_dir / "adapters.yaml", data)

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=tmp_path / "ws_empty",
        )
        result = resolver.get("adapters.yaml")
        assert result == data

    def test_workspace_whole_file_merges_over_global(self, tmp_path: Path):
        """When reading a whole file, workspace keys override global keys."""
        global_dir = tmp_path / "global"
        ws_dir = tmp_path / "ws" / ".nexus"

        _write_yaml(global_dir / "adapters.yaml", {"editor": "neovim", "explorer": "yazi"})
        _write_yaml(ws_dir / "adapters.yaml", {"editor": "helix"})

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=ws_dir,
        )
        result = resolver.get("adapters.yaml")
        assert result["editor"] == "helix"
        assert result["explorer"] == "yazi"

    def test_none_profile_skips_profile_layer(self, tmp_path: Path):
        global_dir = tmp_path / "global"
        _write_yaml(global_dir / "adapters.yaml", {"editor": "neovim"})

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=tmp_path / "ws_empty",
            profile=None,
        )
        assert resolver.get("adapters.yaml", "editor") == "neovim"

    def test_empty_yaml_file_returns_none(self, tmp_path: Path):
        global_dir = tmp_path / "global"
        (global_dir).mkdir(parents=True)
        (global_dir / "empty.yaml").write_text("")

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=tmp_path / "ws_empty",
        )
        assert resolver.get("empty.yaml", "anything") is None


# ---------------------------------------------------------------------------
# T001: ensure_defaults — directory structure creation
# ---------------------------------------------------------------------------

class TestEnsureDefaults:
    """Verify ensure_defaults creates the expected global and workspace scaffolds."""

    def test_creates_global_directory_structure(self, tmp_path: Path):
        global_dir = tmp_path / "config" / "nexus"
        ensure_defaults(global_dir=global_dir)

        assert (global_dir / "adapters.yaml").is_file()
        assert (global_dir / "hud.yaml").is_file()
        assert (global_dir / "connectors.yaml").is_file()
        assert (global_dir / "keymap.conf").is_file()
        assert (global_dir / "theme.yaml").is_file()

        for subdir in ("profiles", "packs", "compositions", "actions", "menus"):
            assert (global_dir / subdir).is_dir()

    def test_creates_workspace_scaffold(self, tmp_path: Path):
        ws_dir = tmp_path / "project" / ".nexus"
        ensure_defaults(workspace_dir=ws_dir)

        assert (ws_dir / "workspace.yaml").is_file()
        for subdir in ("compositions", "actions", "menus"):
            assert (ws_dir / subdir).is_dir()

    def test_global_adapters_defaults(self, tmp_path: Path):
        global_dir = tmp_path / "config" / "nexus"
        ensure_defaults(global_dir=global_dir)

        data = yaml.safe_load((global_dir / "adapters.yaml").read_text())
        assert data["editor"] == "neovim"
        assert data["explorer"] == "yazi"
        assert data["chat"] == "opencode"
        assert data["menu"] == "fzf"
        assert data["multiplexer"] == "tmux"
        assert data["executor"] == "zsh"
        assert data["renderer"] == "bat"

    def test_global_hud_defaults(self, tmp_path: Path):
        global_dir = tmp_path / "config" / "nexus"
        ensure_defaults(global_dir=global_dir)

        data = yaml.safe_load((global_dir / "hud.yaml").read_text())
        assert data["separator"] == " | "
        modules = data["modules"]
        assert len(modules) == 3
        names = [m["name"] for m in modules]
        assert names == ["tabs", "git", "clock"]

    def test_global_connectors_defaults(self, tmp_path: Path):
        global_dir = tmp_path / "config" / "nexus"
        ensure_defaults(global_dir=global_dir)

        data = yaml.safe_load((global_dir / "connectors.yaml").read_text())
        assert data["connectors"] == []

    def test_workspace_yaml_defaults(self, tmp_path: Path):
        ws_dir = tmp_path / "project" / ".nexus"
        ensure_defaults(workspace_dir=ws_dir)

        data = yaml.safe_load((ws_dir / "workspace.yaml").read_text())
        assert data["profile"] is None
        assert data["packs"] == []
        assert data["theme"] is None
        assert data["adapters"] == {}

    def test_does_not_overwrite_existing_files(self, tmp_path: Path):
        global_dir = tmp_path / "config" / "nexus"
        global_dir.mkdir(parents=True)
        (global_dir / "adapters.yaml").write_text("editor: custom\n")

        ensure_defaults(global_dir=global_dir)

        data = yaml.safe_load((global_dir / "adapters.yaml").read_text())
        assert data["editor"] == "custom"

    def test_keymap_conf_has_comment_header(self, tmp_path: Path):
        global_dir = tmp_path / "config" / "nexus"
        ensure_defaults(global_dir=global_dir)

        content = (global_dir / "keymap.conf").read_text()
        assert content.startswith("#")

    def test_theme_yaml_defaults(self, tmp_path: Path):
        global_dir = tmp_path / "config" / "nexus"
        ensure_defaults(global_dir=global_dir)

        data = yaml.safe_load((global_dir / "theme.yaml").read_text())
        assert data["name"] == "nexus-cyber"

    def test_both_global_and_workspace_together(self, tmp_path: Path):
        global_dir = tmp_path / "config" / "nexus"
        ws_dir = tmp_path / "project" / ".nexus"

        ensure_defaults(global_dir=global_dir, workspace_dir=ws_dir)

        assert (global_dir / "adapters.yaml").is_file()
        assert (ws_dir / "workspace.yaml").is_file()
