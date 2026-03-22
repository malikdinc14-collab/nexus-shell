"""Tests for HUD tab status and config handler (T083 / T084)."""

import importlib.util
import os
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))


def _load_module(name, rel_path):
    if name in sys.modules:
        return sys.modules[name]
    full = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load dependencies
_load_module("engine.stacks.stack", "core/engine/stacks/stack.py")
tab_status = _load_module("engine.hud.tab_status", "core/engine/hud/tab_status.py")
config_handler = _load_module(
    "engine.api.config_handler", "core/engine/api/config_handler.py"
)

from engine.stacks.stack import Tab, TabStack  # noqa: E402


# ---------------------------------------------------------------------------
# tab_status — format_tab_indicator
# ---------------------------------------------------------------------------

class TestFormatTabIndicator:
    def test_single_tab_uppercase(self):
        stack = TabStack(pane_id="%1")
        stack.push(Tab(capability_type="editor", adapter_name="neovim"))
        assert tab_status.format_tab_indicator(stack) == "E"

    def test_multiple_tabs_brackets(self):
        stack = TabStack(pane_id="%1")
        stack.push(Tab(capability_type="editor", adapter_name="neovim"))
        stack.push(Tab(capability_type="terminal", adapter_name="zsh"))
        # active_index should be 1 (terminal)
        result = tab_status.format_tab_indicator(stack)
        assert result == "[e|T]"

    def test_empty_stack_dot(self):
        stack = TabStack(pane_id="%1")
        assert tab_status.format_tab_indicator(stack) == "\u00b7"

    def test_respects_active_index(self):
        stack = TabStack(pane_id="%1")
        stack.push(Tab(capability_type="editor", adapter_name="neovim"))
        stack.push(Tab(capability_type="terminal", adapter_name="zsh"))
        stack.push(Tab(capability_type="chat", adapter_name="opencode"))
        # active is last pushed (chat, index 2)
        assert tab_status.format_tab_indicator(stack) == "[e|t|C]"
        # rotate back
        stack.rotate(-1)
        assert tab_status.format_tab_indicator(stack) == "[e|T|c]"

    def test_three_tabs_first_active(self):
        stack = TabStack(pane_id="%1")
        stack.push(Tab(capability_type="editor", adapter_name="neovim"))
        stack.push(Tab(capability_type="terminal", adapter_name="zsh"))
        stack.push(Tab(capability_type="chat", adapter_name="opencode"))
        # rotate to index 0
        stack.rotate(-1)  # now index 1
        stack.rotate(-1)  # now index 0
        assert tab_status.format_tab_indicator(stack) == "[E|t|c]"

    def test_single_terminal_tab(self):
        stack = TabStack(pane_id="%1")
        stack.push(Tab(capability_type="terminal", adapter_name="zsh"))
        assert tab_status.format_tab_indicator(stack) == "T"


# ---------------------------------------------------------------------------
# tab_status — format_pane_status
# ---------------------------------------------------------------------------

class TestFormatPaneStatus:
    def test_multiple_stacks(self):
        s1 = TabStack(pane_id="%1")
        s1.push(Tab(capability_type="editor", adapter_name="neovim"))

        s2 = TabStack(pane_id="%2")
        s2.push(Tab(capability_type="terminal", adapter_name="zsh"))
        s2.push(Tab(capability_type="chat", adapter_name="opencode"))

        result = tab_status.format_pane_status({"%1": s1, "%2": s2})
        assert result == "%1:E %2:[t|C]"

    def test_single_stack(self):
        s1 = TabStack(pane_id="%1")
        s1.push(Tab(capability_type="editor", adapter_name="neovim"))
        result = tab_status.format_pane_status({"%1": s1})
        assert result == "%1:E"

    def test_empty_stacks(self):
        s1 = TabStack(pane_id="%1")
        result = tab_status.format_pane_status({"%1": s1})
        assert result == "%1:\u00b7"

    def test_sorted_pane_order(self):
        s3 = TabStack(pane_id="%3")
        s3.push(Tab(capability_type="chat", adapter_name="opencode"))
        s1 = TabStack(pane_id="%1")
        s1.push(Tab(capability_type="editor", adapter_name="neovim"))
        result = tab_status.format_pane_status({"%3": s3, "%1": s1})
        assert result.startswith("%1:")


# ---------------------------------------------------------------------------
# tab_status — format_hud_line
# ---------------------------------------------------------------------------

class TestFormatHudLine:
    def _make_stacks(self):
        s1 = TabStack(pane_id="%1")
        s1.push(Tab(capability_type="editor", adapter_name="neovim"))
        return {"%1": s1}

    def test_with_profile_and_packs(self):
        result = tab_status.format_hud_line(
            self._make_stacks(), profile_name="devops", pack_count=2
        )
        assert "profile: devops" in result
        assert "packs: 2" in result
        assert "%1:E" in result
        assert " | " in result

    def test_without_profile_omits_section(self):
        result = tab_status.format_hud_line(self._make_stacks(), pack_count=3)
        assert "profile" not in result
        assert "packs: 3" in result

    def test_without_packs_omits_section(self):
        result = tab_status.format_hud_line(
            self._make_stacks(), profile_name="dev"
        )
        assert "packs" not in result
        assert "profile: dev" in result

    def test_no_stacks(self):
        result = tab_status.format_hud_line({})
        assert result == ""

    def test_no_stacks_with_profile(self):
        result = tab_status.format_hud_line({}, profile_name="ops")
        assert result == "profile: ops"

    def test_separator_count(self):
        result = tab_status.format_hud_line(
            self._make_stacks(), profile_name="dev", pack_count=1
        )
        assert result.count(" | ") == 2


# ---------------------------------------------------------------------------
# config_handler — handle_reload
# ---------------------------------------------------------------------------

class TestHandleReload:
    def test_returns_correct_structure(self):
        result = config_handler.handle_reload()
        assert result["action"] == "config_reload"
        assert result["status"] == "ok"
        assert "reloaded" in result

    def test_lists_all_config_types(self):
        result = config_handler.handle_reload()
        for section in ["keymap", "theme", "hud", "adapters", "connectors"]:
            assert section in result["reloaded"]

    def test_with_valid_directory(self):
        with tempfile.TemporaryDirectory() as td:
            result = config_handler.handle_reload(global_dir=td)
            assert result["status"] == "ok"

    def test_missing_directory_returns_error(self):
        result = config_handler.handle_reload(global_dir="/nonexistent/path/xyz")
        assert result["status"] == "error"
        assert result["error"] == "directory_not_found"
        assert result["path"] == "/nonexistent/path/xyz"

    def test_missing_workspace_dir_returns_error(self):
        result = config_handler.handle_reload(workspace_dir="/no/such/dir")
        assert result["status"] == "error"
        assert result["path"] == "/no/such/dir"


# ---------------------------------------------------------------------------
# config_handler — handle_apply_theme
# ---------------------------------------------------------------------------

class TestHandleApplyTheme:
    def test_returns_not_found_with_no_dirs(self):
        result = config_handler.handle_apply_theme("dracula")
        assert result["error"] == "theme_not_found"

    def test_includes_name(self):
        result = config_handler.handle_apply_theme("gruvbox")
        assert result["name"] == "gruvbox"

    def test_apply_with_valid_theme(self, tmp_path):
        theme_dir = tmp_path / "themes"
        theme_dir.mkdir()
        (theme_dir / "solarized.yaml").write_text(
            "name: solarized\ncolors:\n  bg: '#002b36'\n  fg: '#839496'\n"
        )
        result = config_handler.handle_apply_theme("solarized", [str(tmp_path)])
        assert result["action"] == "apply_theme"
        assert result["name"] == "solarized"
        assert "commands" in result


# ---------------------------------------------------------------------------
# config_handler — handle_get
# ---------------------------------------------------------------------------

class TestHandleGet:
    def test_returns_value_structure(self):
        result = config_handler.handle_get("theme.name")
        assert "key" in result
        assert "value" in result
        assert "source" in result

    def test_missing_key_returns_none_value(self):
        result = config_handler.handle_get("nonexistent.key")
        assert result["value"] is None

    def test_includes_source_field(self):
        result = config_handler.handle_get("any.key")
        assert "source" in result

    def test_key_preserved(self):
        result = config_handler.handle_get("hud.position")
        assert result["key"] == "hud.position"
