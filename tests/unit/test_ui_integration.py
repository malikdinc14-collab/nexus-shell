#!/usr/bin/env python3
"""Phase 9 UI integration tests — composition schema, workspace handler, theme engine."""

import importlib.util
import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

COMPOSITIONS_DIR = os.path.join(PROJECT_ROOT, "core", "ui", "compositions")


def _load_module(name, rel_path):
    if name in sys.modules:
        return sys.modules[name]
    full = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# -- Load modules under test ------------------------------------------------

schema_mod = _load_module(
    "core.engine.compositions.schema",
    "core/engine/compositions/schema.py",
)
CompositionPane = schema_mod.CompositionPane
Composition = schema_mod.Composition
load_composition = schema_mod.load_composition
load_compositions_from_directory = schema_mod.load_compositions_from_directory
list_composition_names = schema_mod.list_composition_names

theme_mod = _load_module(
    "core.engine.config.theme_engine",
    "core/engine/config/theme_engine.py",
)
Theme = theme_mod.Theme
load_theme = theme_mod.load_theme
generate_tmux_commands = theme_mod.generate_tmux_commands
handle_apply_theme = theme_mod.handle_apply_theme

# workspace_handler imports schema_mod via absolute import; ensure it resolves
sys.path.insert(0, PROJECT_ROOT)
ws_mod = _load_module(
    "core.engine.api.workspace_handler",
    "core/engine/api/workspace_handler.py",
)
handle_save = ws_mod.handle_save
handle_restore = ws_mod.handle_restore
handle_switch_composition = ws_mod.handle_switch_composition


# ============================================================================
# Composition Schema Tests
# ============================================================================

class TestCompositionPane:
    def test_defaults(self):
        p = CompositionPane(role="editor")
        assert p.role == "editor"
        assert p.width_pct == 50.0
        assert p.height_pct == 100.0
        assert p.command is None
        assert p.split == "h"

    def test_custom_values(self):
        p = CompositionPane(role="terminal", width_pct=30.0, height_pct=70.0,
                            command="zsh", split="v")
        assert p.width_pct == 30.0
        assert p.command == "zsh"
        assert p.split == "v"


class TestComposition:
    def test_defaults(self):
        c = Composition(name="test")
        assert c.name == "test"
        assert c.description == ""
        assert c.panes == []
        assert c.source_file is None

    def test_with_panes(self):
        c = Composition(name="x", panes=[CompositionPane(role="a")])
        assert len(c.panes) == 1


class TestLoadComposition:
    def test_load_valid_json(self, tmp_path):
        data = {
            "name": "demo",
            "description": "Demo layout",
            "layout": {
                "type": "hsplit",
                "panes": [
                    {"id": "left", "size": 60, "command": "vim"},
                    {"id": "right", "command": "zsh"},
                ],
            },
        }
        p = tmp_path / "demo.json"
        p.write_text(json.dumps(data))
        comp = load_composition(str(p))
        assert comp is not None
        assert comp.name == "demo"
        assert len(comp.panes) == 2
        assert comp.panes[0].role == "left"
        assert comp.panes[0].width_pct == 60.0

    def test_returns_none_for_missing_file(self):
        assert load_composition("/nonexistent/path.json") is None

    def test_returns_none_for_bad_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid json!!")
        assert load_composition(str(p)) is None

    def test_direction_schema(self, tmp_path):
        """Direction-based schema (gap-mission style) is normalised correctly."""
        data = {
            "name": "dir_test",
            "description": "direction schema",
            "layout": {
                "direction": "vertical",
                "panes": [
                    {"command": "nvim", "size": "65%", "id": "editor"},
                    {"command": "zsh", "size": "35%", "id": "term"},
                ],
            },
        }
        p = tmp_path / "dir_test.json"
        p.write_text(json.dumps(data))
        comp = load_composition(str(p))
        assert comp is not None
        assert len(comp.panes) == 2
        assert comp.panes[0].width_pct == 100.0  # vertical split keeps width
        assert comp.panes[0].height_pct == 65.0

    def test_load_real_simple(self):
        path = os.path.join(COMPOSITIONS_DIR, "simple.json")
        comp = load_composition(path)
        assert comp is not None
        assert comp.name == "simple"
        assert len(comp.panes) == 2

    def test_load_real_quad(self):
        path = os.path.join(COMPOSITIONS_DIR, "quad.json")
        comp = load_composition(path)
        assert comp is not None
        assert comp.name == "quad"
        assert len(comp.panes) == 4

    def test_load_real_gap_mission(self):
        path = os.path.join(COMPOSITIONS_DIR, "gap-mission.json")
        comp = load_composition(path)
        assert comp is not None
        assert comp.name == "gap-mission"
        assert len(comp.panes) >= 3


class TestLoadCompositionsFromDirectory:
    def test_loads_multiple(self, tmp_path):
        for i in range(3):
            d = {"name": f"c{i}", "layout": {"type": "hsplit", "panes": [
                {"id": "a", "command": "x"}]}}
            (tmp_path / f"c{i}.json").write_text(json.dumps(d))
        comps = load_compositions_from_directory(str(tmp_path))
        assert len(comps) == 3
        assert all(c.source_file is not None for c in comps)

    def test_skips_non_json(self, tmp_path):
        (tmp_path / "readme.txt").write_text("hi")
        (tmp_path / "a.json").write_text(json.dumps(
            {"name": "a", "layout": {"type": "hsplit", "panes": [{"id": "x"}]}}
        ))
        assert len(load_compositions_from_directory(str(tmp_path))) == 1

    def test_empty_dir(self, tmp_path):
        assert load_compositions_from_directory(str(tmp_path)) == []

    def test_missing_dir(self):
        assert load_compositions_from_directory("/no/such/dir") == []


class TestListCompositionNames:
    def test_returns_names(self, tmp_path):
        for n in ["alpha", "beta"]:
            (tmp_path / f"{n}.json").write_text("{}")
        names = list_composition_names(str(tmp_path))
        assert names == ["alpha", "beta"]

    def test_real_compositions_dir(self):
        names = list_composition_names(COMPOSITIONS_DIR)
        assert "simple" in names
        assert "quad" in names
        assert len(names) >= 5


# ============================================================================
# Workspace Handler Tests
# ============================================================================

class TestWorkspaceHandler:
    def test_handle_save_structure(self):
        result = handle_save()
        assert result["action"] == "save_workspace"
        assert result["status"] == "saved"

    def test_handle_restore_structure(self):
        result = handle_restore("my_layout")
        assert result["action"] == "restore_workspace"
        assert result["status"] in ("restored", "error")

    def test_handle_restore_empty_name(self):
        result = handle_restore()
        assert result["action"] == "restore_workspace"

    def test_switch_composition_found(self):
        result = handle_switch_composition("simple")
        assert result["action"] == "switch_composition"
        assert result["name"] == "simple"
        assert result["panes"] == 2

    def test_switch_composition_returns_pane_count(self):
        result = handle_switch_composition("quad")
        assert result["panes"] == 4

    def test_switch_composition_not_found(self):
        result = handle_switch_composition("nonexistent_layout_xyz")
        assert result["error"] == "composition_not_found"
        assert result["name"] == "nonexistent_layout_xyz"
        assert isinstance(result["available"], list)
        assert "simple" in result["available"]


# ============================================================================
# Theme Engine Tests
# ============================================================================

CATPPUCCIN_PATH = os.path.join(
    PROJECT_ROOT, "core", "engine", "config", "themes", "catppuccin.yaml"
)


class TestThemeDataclass:
    def test_defaults(self):
        t = Theme(name="default")
        assert t.name == "default"
        assert t.colors == {}

    def test_with_colors(self):
        t = Theme(name="x", colors={"bg": "#000"})
        assert t.colors["bg"] == "#000"


class TestLoadTheme:
    def test_load_valid_yaml(self):
        t = load_theme(CATPPUCCIN_PATH)
        assert t is not None
        assert t.name == "catppuccin"

    def test_returns_none_for_missing(self):
        assert load_theme("/nonexistent/theme.yaml") is None

    def test_returns_none_for_bad_yaml(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(": : : bad yaml {{{")
        assert load_theme(str(p)) is None


class TestGenerateTmuxCommands:
    def test_includes_status_bg(self):
        t = Theme(name="t", colors={"bg": "#111", "fg": "#eee"})
        cmds = generate_tmux_commands(t)
        assert any("status-bg" in c for c in cmds)

    def test_includes_pane_border_style(self):
        t = Theme(name="t", colors={"fg": "#eee", "border": "#333"})
        cmds = generate_tmux_commands(t)
        assert any("pane-border-style" in c and "#333" in c for c in cmds)

    def test_includes_active_border(self):
        t = Theme(name="t", colors={"accent": "#ff0"})
        cmds = generate_tmux_commands(t)
        assert any("pane-active-border-style" in c and "#ff0" in c for c in cmds)

    def test_uses_fallbacks(self):
        """When specific keys are missing, falls back to bg/fg/accent."""
        t = Theme(name="t", colors={"bg": "#000", "fg": "#fff", "accent": "#0f0"})
        cmds = generate_tmux_commands(t)
        status_bg_cmd = [c for c in cmds if "status-bg" in c][0]
        assert "#000" in status_bg_cmd
        msg_cmd = [c for c in cmds if "message-style" in c][0]
        assert "#000" in msg_cmd  # message_bg falls back to bg
        assert "#0f0" in msg_cmd  # message_fg falls back to accent

    def test_command_count(self):
        t = Theme(name="t", colors={"bg": "#000"})
        cmds = generate_tmux_commands(t)
        assert len(cmds) == 5


class TestHandleApplyTheme:
    def test_found(self):
        config_dir = os.path.join(PROJECT_ROOT, "core", "engine", "config")
        result = handle_apply_theme("catppuccin", [config_dir])
        assert result["action"] == "apply_theme"
        assert result["name"] == "catppuccin"
        assert isinstance(result["commands"], list)
        assert len(result["commands"]) > 0

    def test_not_found(self):
        result = handle_apply_theme("nonexistent_theme", ["/tmp"])
        assert result["error"] == "theme_not_found"
        assert result["name"] == "nonexistent_theme"


class TestCatppuccin:
    def test_loads_correctly(self):
        t = load_theme(CATPPUCCIN_PATH)
        assert t is not None
        assert t.name == "catppuccin"
        assert t.colors["bg"] == "#1e1e2e"
        assert t.colors["accent"] == "#89b4fa"

    def test_generates_valid_commands(self):
        t = load_theme(CATPPUCCIN_PATH)
        cmds = generate_tmux_commands(t)
        assert len(cmds) == 5
        assert any("#1e1e2e" in c for c in cmds)
        assert any("#89b4fa" in c for c in cmds)
