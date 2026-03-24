#!/usr/bin/env python3
"""
Unit tests for the project-local configuration system (Phase 4A).

Covers:
  - T001: Project discovery — detect .nexus/, parse boot/menu/profile
  - T002: Boot runner — blocking/background execution, shutdown
  - T003: Project menu — load commands as Command Graph nodes
  - T004: NexusCore integration — discover_project, run_boot, get_project_menu_nodes
  - T005: CLI dispatch — nexus-ctl project subcommands

No live filesystem side-effects — all paths use tmp_path fixtures.
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from engine.project.discovery import discover, ProjectConfig, NEXUS_DIR
from engine.project.boot import BootRunner, BootResult, BootProcess
from engine.project.menu import load_project_menu
from engine.graph.node import NodeType, ActionKind, Scope


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False))


def _make_nexus_dir(tmp_path: Path) -> Path:
    """Create a .nexus/ directory and return the project root."""
    nexus = tmp_path / NEXUS_DIR
    nexus.mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# T001: Project Discovery
# ---------------------------------------------------------------------------

class TestProjectDiscovery:
    """Test .nexus/ directory detection and parsing."""

    def test_no_nexus_dir_returns_none(self, tmp_path):
        assert discover(tmp_path) is None

    def test_empty_nexus_dir_returns_config(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        config = discover(root)
        assert config is not None
        assert config.root == root.resolve()
        assert config.boot_items == []
        assert config.menu_path is None
        assert config.profile is None

    def test_boot_yaml_parsed(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "boot.yaml", [
            {"label": "start db", "run": "echo db", "wait": True},
            {"label": "start server", "run": "echo server", "wait": False},
        ])
        config = discover(root)
        assert len(config.boot_items) == 2
        assert config.boot_items[0]["label"] == "start db"
        assert config.boot_items[0]["wait"] is True
        assert config.boot_items[1]["wait"] is False

    def test_boot_yaml_missing_run_skipped(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "boot.yaml", [
            {"label": "no run field"},
            {"label": "valid", "run": "echo ok"},
        ])
        config = discover(root)
        assert len(config.boot_items) == 1
        assert config.boot_items[0]["label"] == "valid"

    def test_boot_yaml_not_a_list(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "boot.yaml", {"not": "a list"})
        config = discover(root)
        assert config.boot_items == []

    def test_menu_yaml_detected(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        menu_path = root / NEXUS_DIR / "menu.yaml"
        _write_yaml(menu_path, {"commands": []})
        config = discover(root)
        assert config.menu_path == menu_path

    def test_profile_yaml_parsed(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "profile.yaml", {
            "profile": "focused",
            "theme": "catppuccin",
            "composition": "dual",
        })
        config = discover(root)
        assert config.profile == "focused"
        assert config.theme == "catppuccin"
        assert config.composition == "dual"

    def test_profile_yaml_partial(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "profile.yaml", {"profile": "dashboard"})
        config = discover(root)
        assert config.profile == "dashboard"
        assert config.theme is None
        assert config.composition is None

    def test_connectors_yaml_detected(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        conn_path = root / NEXUS_DIR / "connectors.yaml"
        _write_yaml(conn_path, {"connectors": []})
        config = discover(root)
        assert config.connectors_path == conn_path

    def test_boot_item_default_values(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "boot.yaml", [
            {"run": "echo hello"},
        ])
        config = discover(root)
        item = config.boot_items[0]
        assert item["label"] == "boot-0"
        assert item["wait"] is False
        assert item["health"] is None
        assert item["env"] == {}

    def test_boot_item_with_env(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "boot.yaml", [
            {"label": "with env", "run": "echo $FOO", "env": {"FOO": "bar"}},
        ])
        config = discover(root)
        assert config.boot_items[0]["env"] == {"FOO": "bar"}


# ---------------------------------------------------------------------------
# T002: Boot Runner
# ---------------------------------------------------------------------------

class TestBootRunner:
    """Test boot list execution."""

    def test_empty_items_returns_zero_result(self):
        runner = BootRunner()
        result = runner.run([])
        assert result.total == 0
        assert result.success

    def test_blocking_success(self, tmp_path):
        runner = BootRunner()
        result = runner.run([
            {"label": "echo test", "run": "echo hello", "wait": True},
        ], cwd=str(tmp_path))
        assert result.total == 1
        assert result.completed == 1
        assert result.failed == 0
        assert result.success

    def test_blocking_failure(self, tmp_path):
        runner = BootRunner()
        result = runner.run([
            {"label": "fail", "run": "exit 1", "wait": True},
        ], cwd=str(tmp_path))
        assert result.failed == 1
        assert not result.success
        assert len(result.errors) == 1

    def test_background_process_tracked(self, tmp_path):
        runner = BootRunner()
        result = runner.run([
            {"label": "sleeper", "run": "sleep 60", "wait": False},
        ], cwd=str(tmp_path))
        assert result.background == 1
        assert result.completed == 1
        assert len(runner.processes) == 1
        # Cleanup
        runner.shutdown()

    def test_shutdown_kills_processes(self, tmp_path):
        runner = BootRunner()
        runner.run([
            {"label": "sleeper", "run": "sleep 60", "wait": False},
        ], cwd=str(tmp_path))
        assert len(runner.processes) == 1
        killed = runner.shutdown()
        assert killed == 1
        assert len(runner.processes) == 0

    def test_multiple_items_sequential(self, tmp_path):
        marker = tmp_path / "marker.txt"
        runner = BootRunner()
        result = runner.run([
            {"label": "create", "run": f"touch {marker}", "wait": True},
            {"label": "check", "run": f"test -f {marker}", "wait": True},
        ], cwd=str(tmp_path))
        assert result.completed == 2
        assert result.failed == 0

    def test_failed_item_doesnt_block_rest(self, tmp_path):
        runner = BootRunner()
        result = runner.run([
            {"label": "fail", "run": "exit 1", "wait": True},
            {"label": "succeed", "run": "echo ok", "wait": True},
        ], cwd=str(tmp_path))
        assert result.completed == 1
        assert result.failed == 1

    def test_progress_callback(self, tmp_path):
        progress_calls = []

        def on_progress(current, total, label):
            progress_calls.append((current, total, label))

        runner = BootRunner(on_progress=on_progress)
        runner.run([
            {"label": "step1", "run": "echo 1", "wait": True},
            {"label": "step2", "run": "echo 2", "wait": True},
        ], cwd=str(tmp_path))
        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 2, "step1")
        assert progress_calls[1] == (2, 2, "step2")

    def test_env_override(self, tmp_path):
        out_file = tmp_path / "env_out.txt"
        runner = BootRunner()
        result = runner.run([
            {"label": "env test", "run": f"echo $TEST_VAR > {out_file}", "wait": True},
        ], cwd=str(tmp_path), env_override={"TEST_VAR": "nexus_test"})
        assert result.success
        assert "nexus_test" in out_file.read_text()

    def test_item_level_env(self, tmp_path):
        out_file = tmp_path / "item_env.txt"
        runner = BootRunner()
        result = runner.run([
            {
                "label": "item env",
                "run": f"echo $ITEM_VAR > {out_file}",
                "wait": True,
                "env": {"ITEM_VAR": "from_item"},
            },
        ], cwd=str(tmp_path))
        assert result.success
        assert "from_item" in out_file.read_text()


# ---------------------------------------------------------------------------
# T003: Project Menu
# ---------------------------------------------------------------------------

class TestProjectMenu:
    """Test project menu loading into Command Graph nodes."""

    def test_no_file_returns_empty(self, tmp_path):
        nodes = load_project_menu(tmp_path / "nonexistent.yaml")
        assert nodes == []

    def test_valid_menu(self, tmp_path):
        menu_path = tmp_path / "menu.yaml"
        _write_yaml(menu_path, {
            "commands": [
                {"id": "test", "label": "Run Tests", "run": "pytest", "description": "Run test suite"},
                {"id": "build", "label": "Build", "run": "make build"},
            ]
        })
        nodes = load_project_menu(menu_path)
        assert len(nodes) == 2
        assert nodes[0].id == "project:test"
        assert nodes[0].label == "Run Tests"
        assert nodes[0].command == "pytest"
        assert nodes[0].type == NodeType.ACTION
        assert nodes[0].scope == Scope.WORKSPACE
        assert nodes[0].action_kind == ActionKind.SHELL
        assert "project" in nodes[0].tags

    def test_missing_id_skipped(self, tmp_path):
        menu_path = tmp_path / "menu.yaml"
        _write_yaml(menu_path, {
            "commands": [
                {"label": "No ID", "run": "echo"},
                {"id": "valid", "label": "Valid", "run": "echo ok"},
            ]
        })
        nodes = load_project_menu(menu_path)
        assert len(nodes) == 1
        assert nodes[0].id == "project:valid"

    def test_missing_run_skipped(self, tmp_path):
        menu_path = tmp_path / "menu.yaml"
        _write_yaml(menu_path, {
            "commands": [
                {"id": "no-run", "label": "No run"},
            ]
        })
        nodes = load_project_menu(menu_path)
        assert len(nodes) == 0

    def test_tags_merged(self, tmp_path):
        menu_path = tmp_path / "menu.yaml"
        _write_yaml(menu_path, {
            "commands": [
                {"id": "tagged", "label": "Tagged", "run": "echo", "tags": ["ci", "deploy"]},
            ]
        })
        nodes = load_project_menu(menu_path)
        assert "ci" in nodes[0].tags
        assert "deploy" in nodes[0].tags
        assert "project" in nodes[0].tags

    def test_empty_commands_list(self, tmp_path):
        menu_path = tmp_path / "menu.yaml"
        _write_yaml(menu_path, {"commands": []})
        nodes = load_project_menu(menu_path)
        assert nodes == []

    def test_not_a_dict_returns_empty(self, tmp_path):
        menu_path = tmp_path / "menu.yaml"
        _write_yaml(menu_path, [1, 2, 3])
        nodes = load_project_menu(menu_path)
        assert nodes == []


# ---------------------------------------------------------------------------
# T004: NexusCore Integration
# ---------------------------------------------------------------------------

class TestNexusCoreProject:
    """Test NexusCore.discover_project and related methods."""

    def _make_core(self, tmp_path):
        """Create a NexusCore with NullSurface."""
        from engine.surfaces import NullSurface
        from engine.core import NexusCore
        return NexusCore(
            surface=NullSurface(),
            config_dir=str(tmp_path / "config"),
            workspace_dir=str(tmp_path / "ws"),
        )

    def test_discover_no_nexus(self, tmp_path):
        core = self._make_core(tmp_path)
        result = core.discover_project(str(tmp_path))
        assert result is None
        assert core.project is None

    def test_discover_with_nexus(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "profile.yaml", {"profile": "focused"})
        core = self._make_core(tmp_path)
        config = core.discover_project(str(root))
        assert config is not None
        assert config.profile == "focused"
        assert core.project is config

    def test_discover_updates_cascade_resolver(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "profile.yaml", {"profile": "focused"})
        # Write a config file into .nexus/ for cascade testing
        _write_yaml(root / NEXUS_DIR / "settings.yaml", {"color": "blue"})
        core = self._make_core(tmp_path)
        core.discover_project(str(root))
        # Cascade should resolve from .nexus/
        assert core.config.get("settings.yaml", "color") == "blue"

    def test_run_boot_no_project(self, tmp_path):
        core = self._make_core(tmp_path)
        result = core.run_boot()
        assert result is None

    def test_run_boot_with_items(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        marker = tmp_path / "booted.txt"
        _write_yaml(root / NEXUS_DIR / "boot.yaml", [
            {"label": "mark", "run": f"touch {marker}", "wait": True},
        ])
        core = self._make_core(tmp_path)
        core.discover_project(str(root))
        result = core.run_boot()
        assert result is not None
        assert result.success
        assert marker.exists()

    def test_shutdown_boot(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "boot.yaml", [
            {"label": "sleeper", "run": "sleep 60", "wait": False},
        ])
        core = self._make_core(tmp_path)
        core.discover_project(str(root))
        core.run_boot()
        killed = core.shutdown_boot()
        assert killed == 1

    def test_get_project_menu_nodes(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "menu.yaml", {
            "commands": [
                {"id": "test", "label": "Test", "run": "pytest"},
            ]
        })
        core = self._make_core(tmp_path)
        core.discover_project(str(root))
        nodes = core.get_project_menu_nodes()
        assert len(nodes) == 1
        assert nodes[0].id == "project:test"

    def test_get_project_menu_no_project(self, tmp_path):
        core = self._make_core(tmp_path)
        nodes = core.get_project_menu_nodes()
        assert nodes == []

    def test_boot_events_published(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "boot.yaml", [
            {"label": "step", "run": "echo ok", "wait": True},
        ])
        core = self._make_core(tmp_path)
        events = []
        core.bus.subscribe("boot.*", lambda e: events.append(e.source))
        core.discover_project(str(root))
        core.run_boot()
        assert "boot.start" in events
        assert "boot.progress" in events
        assert "boot.complete" in events

    def test_project_discovered_event(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        core = self._make_core(tmp_path)
        events = []
        core.bus.subscribe("project.*", lambda e: events.append(e.source))
        core.discover_project(str(root))
        assert "project.discovered" in events


# ---------------------------------------------------------------------------
# T005: CLI Dispatch
# ---------------------------------------------------------------------------

class TestCLIProject:
    """Test nexus-ctl project subcommands."""

    def test_project_info_no_nexus(self, tmp_path):
        from engine.cli.nexus_ctl import main
        with patch("os.getcwd", return_value=str(tmp_path)):
            result = main(["project", "info"])
        assert result is not None
        assert result["found"] is False

    def test_project_info_with_nexus(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "profile.yaml", {"profile": "focused"})
        _write_yaml(root / NEXUS_DIR / "boot.yaml", [
            {"label": "test", "run": "echo ok", "wait": True},
        ])
        from engine.cli.nexus_ctl import main
        with patch("os.getcwd", return_value=str(root)):
            result = main(["project", "info"])
        assert result["found"] is True
        assert result["boot_items"] == 1
        assert result["profile"] == "focused"

    def test_project_menu_command(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        _write_yaml(root / NEXUS_DIR / "menu.yaml", {
            "commands": [
                {"id": "lint", "label": "Lint", "run": "flake8"},
            ]
        })
        from engine.cli.nexus_ctl import main
        with patch("os.getcwd", return_value=str(root)):
            result = main(["project", "menu"])
        assert len(result["commands"]) == 1
        assert result["commands"][0]["id"] == "project:lint"

    def test_project_discover_custom_dir(self, tmp_path):
        root = _make_nexus_dir(tmp_path)
        from engine.cli.nexus_ctl import main
        result = main(["project", "discover", "--dir", str(root)])
        assert result["found"] is True

    def test_project_boot_no_items(self, tmp_path):
        from engine.cli.nexus_ctl import main
        with patch("os.getcwd", return_value=str(tmp_path)):
            result = main(["project", "boot"])
        assert result["status"] == "no_boot_items"
