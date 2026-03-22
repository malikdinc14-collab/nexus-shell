"""Tests for HUD module framework — resolvers, registry, and renderer."""
import sys
import os

# Ensure engine package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))

from engine.hud.module import (
    BUILTIN_RESOLVERS,
    HudModuleResult,
    resolve_module,
    _git_branch,
    _clock,
    _python_version,
    _word_count,
    _cpu,
    _memory,
)
from engine.hud.renderer import render_hud_line, render_tmux_status


# ---------------------------------------------------------------------------
# Built-in resolver tests
# ---------------------------------------------------------------------------

class TestBuiltinResolvers:
    """Each built-in resolver must return a HudModuleResult with non-empty text."""

    def test_git_branch_returns_result(self):
        result = _git_branch()
        assert isinstance(result, HudModuleResult)
        assert len(result.text) > 0

    def test_clock_returns_result(self):
        result = _clock()
        assert isinstance(result, HudModuleResult)
        assert len(result.text) > 0
        # Should look like HH:MM
        assert ":" in result.text

    def test_python_version_returns_result(self):
        result = _python_version()
        assert isinstance(result, HudModuleResult)
        assert result.text.startswith("py")

    def test_word_count_returns_result(self):
        result = _word_count()
        assert isinstance(result, HudModuleResult)
        assert len(result.text) > 0

    def test_cpu_returns_result(self):
        result = _cpu()
        assert isinstance(result, HudModuleResult)
        assert result.text.startswith("cpu:")

    def test_memory_returns_result(self):
        result = _memory()
        assert isinstance(result, HudModuleResult)
        assert result.text.startswith("mem:")


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestResolverRegistry:
    """Tests for the BUILTIN_RESOLVERS registry and resolve_module function."""

    def test_registry_has_at_least_5_entries(self):
        assert len(BUILTIN_RESOLVERS) >= 5

    def test_registry_contains_expected_keys(self):
        expected = {"git_branch", "clock", "python_version", "cpu", "memory"}
        assert expected.issubset(set(BUILTIN_RESOLVERS.keys()))

    def test_resolve_module_known_id(self):
        result = resolve_module("clock")
        assert isinstance(result, HudModuleResult)
        assert ":" in result.text  # HH:MM format

    def test_resolve_module_unknown_id_returns_placeholder(self):
        result = resolve_module("nonexistent_widget")
        assert isinstance(result, HudModuleResult)
        assert result.text == "nonexistent_widget:--"

    def test_all_registered_resolvers_callable(self):
        for name, fn in BUILTIN_RESOLVERS.items():
            assert callable(fn), f"Resolver '{name}' is not callable"


# ---------------------------------------------------------------------------
# Renderer tests
# ---------------------------------------------------------------------------

class TestHudRenderer:
    """Tests for render_hud_line and render_tmux_status."""

    def test_render_hud_line_multiple_modules(self):
        line = render_hud_line(["clock", "python_version"])
        assert " | " in line  # default separator

    def test_render_hud_line_custom_separator(self):
        line = render_hud_line(["clock", "python_version"], separator=" :: ")
        assert " :: " in line

    def test_render_hud_line_tabs_placeholder(self):
        line = render_hud_line(["clock", "tabs", "python_version"])
        assert "[tabs]" in line

    def test_render_hud_line_single_module(self):
        line = render_hud_line(["clock"])
        assert len(line) > 0
        assert " | " not in line  # no separator for single item

    def test_render_hud_line_empty_list(self):
        line = render_hud_line([])
        assert line == ""

    def test_render_tmux_status_delegates_to_hud_line(self):
        line = render_tmux_status(["clock"])
        assert len(line) > 0

    def test_render_hud_line_unknown_module_shows_placeholder(self):
        line = render_hud_line(["bogus_module"])
        assert "bogus_module:--" in line

    def test_render_hud_line_icon_prefix(self):
        # git_branch has icon="branch"
        line = render_hud_line(["git_branch"])
        # Should have "branch:" prefix from the icon
        assert "branch:" in line or "no-repo" in line
