#!/usr/bin/env python3
# tests/unit/test_nexus_ctl_cli.py
"""
Unit tests for the nexus-ctl domain-based CLI (core/engine/cli/nexus_ctl.py).

Validates:
  - --help returns exit 0
  - No-arg invocation prints help and exits 1
  - Domain dispatch returns valid results from handlers
  - All domain subparsers are registered
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Ensure core/ is on sys.path for engine.X imports
sys.path.insert(0, str(PROJECT_ROOT / "core"))


def _load_module(name, rel_path):
    if name in sys.modules:
        return sys.modules[name]
    full = PROJECT_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load dependencies needed by handlers
_load_module("engine.stacks.stack", "core/engine/stacks/stack.py")
_load_module("engine.stacks.reservoir", "core/engine/stacks/reservoir.py")
_load_module("engine.stacks.manager", "core/engine/stacks/manager.py")
_load_module("engine.api.runtime", "core/engine/api/runtime.py")
_load_module("engine.api.stack_handler", "core/engine/api/stack_handler.py")
_load_module("engine.api.pane_handler", "core/engine/api/pane_handler.py")
_load_module("engine.api.tab_manager", "core/engine/api/tab_manager.py")
_load_module("engine.graph.node", "core/engine/graph/node.py")
_load_module("engine.graph.loader", "core/engine/graph/loader.py")
_load_module("engine.api.menu_handler", "core/engine/api/menu_handler.py")
_load_module("engine.api.workspace_handler", "core/engine/api/workspace_handler.py")
_load_module("engine.compositions.schema", "core/engine/compositions/schema.py")
_load_module("engine.api.config_handler", "core/engine/api/config_handler.py")
_load_module("engine.bus.typed_events", "core/engine/bus/typed_events.py")
_load_module("engine.bus.enhanced_bus", "core/engine/bus/enhanced_bus.py")
_load_module("engine.api.bus_handler", "core/engine/api/bus_handler.py")
_load_module("engine.packs.pack", "core/engine/packs/pack.py")
_load_module("engine.packs.detector", "core/engine/packs/detector.py")
_load_module("engine.packs.manager", "core/engine/packs/manager.py")
_load_module("engine.profiles.manager", "core/engine/profiles/manager.py")

cli_mod = _load_module("nexus_ctl_cli", "core/engine/cli/nexus_ctl.py")
cli_main = cli_mod.main

runtime_mod = sys.modules["engine.api.runtime"]


@pytest.fixture(autouse=True)
def reset_runtime():
    """Reset shared state between tests."""
    runtime_mod.reset()
    yield
    runtime_mod.reset()


# ── Help flag ────────────────────────────────────────────────────────────────

class TestHelpFlag:
    def test_help_returns_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--help"])
        assert exc_info.value.code == 0

    def test_help_output_contains_prog_name(self, capsys):
        with pytest.raises(SystemExit):
            cli_main(["--help"])
        out = capsys.readouterr().out
        assert "nexus-ctl" in out


# ── No-args invocation ───────────────────────────────────────────────────────

class TestNoArgs:
    def test_no_args_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc_info:
            cli_main([])
        assert exc_info.value.code == 1

    def test_no_args_prints_help(self, capsys):
        with pytest.raises(SystemExit):
            cli_main([])
        out = capsys.readouterr().out
        assert "nexus-ctl" in out


# ── Domain dispatch ──────────────────────────────────────────────────────────

class TestDomainDispatch:
    def test_menu_open_returns_items(self):
        result = cli_main(["menu", "open"])
        assert result["action"] == "show_menu"
        assert "items" in result

    def test_stack_push_returns_result(self):
        result = cli_main(["stack", "push"])
        assert result is not None
        assert "action" in result
        assert result["action"] == "push"

    def test_stack_pop_on_empty(self):
        result = cli_main(["stack", "pop"])
        assert result is not None
        assert result["status"] == "empty"

    def test_stack_rotate_positive(self):
        result = cli_main(["stack", "rotate", "1"])
        assert result is not None
        assert result["action"] == "rotate"

    def test_tabs_list_empty(self):
        result = cli_main(["tabs", "list"])
        assert result is not None
        assert result["tabs"] == []

    def test_pane_kill_empty(self):
        result = cli_main(["pane", "kill"])
        assert result is not None
        assert result["action"] == "kill_pane"

    def test_pane_split_v(self):
        result = cli_main(["pane", "split-v"])
        assert result is not None
        assert result["action"] == "split"
        assert result["direction"] == "v"

    def test_pane_split_h(self):
        result = cli_main(["pane", "split-h"])
        assert result is not None
        assert result["action"] == "split"
        assert result["direction"] == "h"

    def test_workspace_save(self):
        result = cli_main(["workspace", "save"])
        assert result is not None
        assert result["action"] == "save_workspace"

    def test_workspace_restore(self):
        result = cli_main(["workspace", "restore"])
        assert result is not None
        assert result["action"] == "restore_workspace"

    def test_bus_publish_runs(self):
        result = cli_main(["bus", "publish", "test.event", '{"key":"val"}'])
        assert result["status"] == "ok"
        assert result["event_type"] == "test.event"

    def test_bus_history(self):
        result = cli_main(["bus", "history"])
        assert result["status"] == "ok"
        assert "events" in result

    def test_config_reload(self):
        result = cli_main(["config", "reload"])
        assert result is not None
        assert result["action"] == "config_reload"

    def test_pack_list(self):
        result = cli_main(["pack", "list"])
        assert result is not None
        assert "packs" in result

    def test_pack_enable_unknown(self):
        result = cli_main(["pack", "enable", "nonexistent"])
        assert result is not None
        assert result["enabled"] is False

    def test_profile_list(self):
        result = cli_main(["profile", "list"])
        assert result is not None
        assert "profiles" in result

    def test_profile_switch_unknown(self):
        result = cli_main(["profile", "switch", "nonexistent"])
        assert result is not None
        assert result["switched"] is False


# ── All domains registered ───────────────────────────────────────────────────

class TestAllDomainsRegistered:
    EXPECTED_DOMAINS = [
        "menu", "capability", "stack", "tabs", "pane",
        "workspace", "pack", "profile", "config", "bus",
    ]

    @pytest.mark.parametrize("domain", EXPECTED_DOMAINS)
    def test_domain_accepted(self, domain):
        """Each domain should be a valid first argument (no 'invalid choice' error)."""
        try:
            cli_main([domain])
        except SystemExit as e:
            # exit 0 or 1 are both fine; argparse error would be exit 2
            assert e.code != 2, f"Domain '{domain}' not recognized by argparse"


# ── Shell wrapper existence ──────────────────────────────────────────────────

class TestShellWrapper:
    def test_bin_wrapper_exists_and_executable(self):
        wrapper = PROJECT_ROOT / "bin" / "nexus-ctl"
        assert wrapper.exists(), "bin/nexus-ctl must exist"
        assert wrapper.stat().st_mode & 0o111, "bin/nexus-ctl must be executable"
