#!/usr/bin/env python3
# tests/unit/test_keymap_e2e.py
"""
End-to-end keymap integration tests for nexus-shell (T024).

Verifies all keybindings in nexus.conf are complete, route correctly,
and that keymap_loader functions work as expected.

This is a static analysis test — no tmux process is needed.
"""

import importlib.util
import os
import re
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

NEXUS_CONF = os.path.join(PROJECT_ROOT, "config", "tmux", "nexus.conf")


def _load_module(name, rel_path):
    if name in sys.modules:
        return sys.modules[name]
    full = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


keymap_loader = _load_module(
    "nexus_keymap_loader", "core/engine/config/keymap_loader.py"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_nexus_conf():
    """Read nexus.conf and return its content as a string."""
    with open(NEXUS_CONF, "r") as f:
        return f.read()


def _extract_bind_n_lines(content):
    """Extract all 'bind-key -n M-...' lines from nexus.conf content."""
    return [
        line.strip()
        for line in content.splitlines()
        if re.match(r"^\s*bind-key\s+-n\s+M-", line)
    ]


def _extract_bind_n_keys(content):
    """Return set of Alt key letters/symbols from bind-key -n M-{key} lines."""
    keys = set()
    for line in content.splitlines():
        m = re.match(r"^\s*bind-key\s+-n\s+M-(\S+)", line)
        if m:
            keys.add(m.group(1))
    return keys


CONF_CONTENT = _read_nexus_conf()
BIND_N_LINES = _extract_bind_n_lines(CONF_CONTENT)
BIND_N_KEYS = _extract_bind_n_keys(CONF_CONTENT)


# ---------------------------------------------------------------------------
# Section 4.1 Required Bindings (13 Alt+key)
# ---------------------------------------------------------------------------

# The 13 required Alt+key bindings from design section 4.1:
REQUIRED_ALT_KEYS = {
    "h", "j", "k", "l",   # Navigation
    "m", "o", "t",         # Command graph & launchers
    "n", "w",              # Tab stack push/pop
    "q", "v", "s",         # Pane operations
    "z",                   # Focus (zoom)
}


class TestRequiredBindingsExist:
    """All 13 Alt+key bindings from design Section 4.1 exist in nexus.conf."""

    def test_all_13_required_alt_keys_present(self):
        missing = REQUIRED_ALT_KEYS - BIND_N_KEYS
        assert not missing, f"Missing required Alt+key bindings: {missing}"

    def test_exact_count_at_least_13(self):
        # There may be more (like Alt+g, Alt+[, Alt+]), but at least 13
        assert len(BIND_N_KEYS) >= 13


class TestBindingFormat:
    """All bindings use correct tmux format."""

    def test_all_use_bind_key_n_no_prefix(self):
        """All Alt+key bindings use 'bind-key -n' (no prefix required)."""
        for line in BIND_N_LINES:
            assert line.startswith("bind-key -n"), (
                f"Binding does not use 'bind-key -n': {line}"
            )

    def test_nexus_ctl_bindings_use_run_shell(self):
        """All nexus-ctl bindings use run-shell format."""
        for line in BIND_N_LINES:
            if "nexus-ctl" in line:
                assert "run-shell" in line, (
                    f"nexus-ctl binding missing run-shell: {line}"
                )

    def test_navigation_hjkl_use_select_pane(self):
        """Navigation bindings (h/j/k/l) use select-pane."""
        nav_keys = {"M-h", "M-j", "M-k", "M-l"}
        for line in BIND_N_LINES:
            parts = line.split()
            # parts: ['bind-key', '-n', 'M-h', 'select-pane', '-L']
            if len(parts) >= 3 and parts[2] in nav_keys:
                assert "select-pane" in line, (
                    f"Navigation binding should use select-pane: {line}"
                )


class TestSpecificBindings:
    """Verify specific important bindings exist."""

    def test_alt_z_zoom_exists(self):
        assert "z" in BIND_N_KEYS, "Alt+z (zoom) binding missing"

    def test_alt_z_uses_resize_pane_Z(self):
        zoom_lines = [l for l in BIND_N_LINES if "M-z" in l]
        assert any("resize-pane -Z" in l for l in zoom_lines), (
            "Alt+z should use resize-pane -Z"
        )

    def test_alt_g_lazygit_exists(self):
        assert "g" in BIND_N_KEYS, "Alt+g (lazygit) binding missing"

    def test_alt_g_uses_lazygit(self):
        git_lines = [l for l in BIND_N_LINES if "M-g" in l]
        assert any("lazygit" in l for l in git_lines), (
            "Alt+g should invoke lazygit"
        )


class TestNoStaleBindings:
    """No stale bindings to removed scripts."""

    def test_no_mosaic_engine_references(self):
        assert "mosaic_engine" not in CONF_CONTENT, (
            "Found stale reference to mosaic_engine"
        )

    def test_no_swap_sh_references(self):
        assert "swap.sh" not in CONF_CONTENT, (
            "Found stale reference to swap.sh"
        )

    def test_no_tree_swap_references(self):
        assert "tree_swap" not in CONF_CONTENT, (
            "Found stale reference to tree_swap"
        )


# ---------------------------------------------------------------------------
# keymap_loader unit tests
# ---------------------------------------------------------------------------

class TestParseKeymap:
    """Tests for keymap_loader.parse_keymap."""

    def test_parses_sample_entries(self, tmp_path):
        conf = tmp_path / "keymap.conf"
        conf.write_text(
            "Alt+F5 = nexus-ctl workspace save\n"
            "Alt+p = nexus-ctl pack suggest\n"
        )
        result = keymap_loader.parse_keymap(str(conf))
        assert result == [
            ("M-F5", "nexus-ctl workspace save"),
            ("M-p", "nexus-ctl pack suggest"),
        ]

    def test_ignores_comments_and_blanks(self, tmp_path):
        conf = tmp_path / "keymap.conf"
        conf.write_text(
            "# This is a comment\n"
            "\n"
            "Alt+a = nexus-ctl do-thing\n"
            "  # Another comment\n"
            "\n"
        )
        result = keymap_loader.parse_keymap(str(conf))
        assert len(result) == 1
        assert result[0] == ("M-a", "nexus-ctl do-thing")

    def test_returns_empty_for_missing_file(self):
        result = keymap_loader.parse_keymap("/nonexistent/keymap.conf")
        assert result == []

    def test_handles_equals_in_command(self, tmp_path):
        conf = tmp_path / "keymap.conf"
        conf.write_text("Alt+x = nexus-ctl set key=value\n")
        result = keymap_loader.parse_keymap(str(conf))
        assert result == [("M-x", "nexus-ctl set key=value")]


class TestGenerateBindings:
    """Tests for keymap_loader.generate_bindings."""

    def test_produces_correct_tmux_commands(self):
        entries = [
            ("M-F5", "nexus-ctl workspace save"),
            ("M-p", "nexus-ctl pack suggest"),
        ]
        result = keymap_loader.generate_bindings(entries)
        assert result == [
            'bind-key -n M-F5 run-shell "nexus-ctl workspace save"',
            'bind-key -n M-p run-shell "nexus-ctl pack suggest"',
        ]

    def test_empty_entries_returns_empty(self):
        assert keymap_loader.generate_bindings([]) == []


class TestLoadKeymapCascade:
    """Tests for keymap_loader.load_keymap_cascade."""

    def test_workspace_overrides_global(self, tmp_path):
        global_dir = tmp_path / "global"
        ws_dir = tmp_path / "workspace"
        global_dir.mkdir()
        ws_dir.mkdir()

        (global_dir / "keymap.conf").write_text(
            "Alt+a = nexus-ctl global-action\n"
            "Alt+b = nexus-ctl global-b\n"
        )
        (ws_dir / "keymap.conf").write_text(
            "Alt+a = nexus-ctl workspace-action\n"
        )

        result = keymap_loader.load_keymap_cascade(
            str(global_dir), workspace_dir=str(ws_dir)
        )
        # Alt+a should be workspace version, Alt+b should be global
        assert 'bind-key -n M-a run-shell "nexus-ctl workspace-action"' in result
        assert 'bind-key -n M-b run-shell "nexus-ctl global-b"' in result
        assert 'bind-key -n M-a run-shell "nexus-ctl global-action"' not in result

    def test_profile_overrides_global(self, tmp_path):
        global_dir = tmp_path / "global"
        profile_dir = tmp_path / "profile"
        global_dir.mkdir()
        profile_dir.mkdir()

        (global_dir / "keymap.conf").write_text("Alt+x = nexus-ctl g\n")
        (profile_dir / "keymap.conf").write_text("Alt+x = nexus-ctl p\n")

        result = keymap_loader.load_keymap_cascade(
            str(global_dir), profile_dir=str(profile_dir)
        )
        assert 'bind-key -n M-x run-shell "nexus-ctl p"' in result

    def test_workspace_overrides_profile_overrides_global(self, tmp_path):
        global_dir = tmp_path / "global"
        profile_dir = tmp_path / "profile"
        ws_dir = tmp_path / "workspace"
        for d in [global_dir, profile_dir, ws_dir]:
            d.mkdir()

        (global_dir / "keymap.conf").write_text("Alt+z = nexus-ctl g\n")
        (profile_dir / "keymap.conf").write_text("Alt+z = nexus-ctl p\n")
        (ws_dir / "keymap.conf").write_text("Alt+z = nexus-ctl w\n")

        result = keymap_loader.load_keymap_cascade(
            str(global_dir),
            workspace_dir=str(ws_dir),
            profile_dir=str(profile_dir),
        )
        assert 'bind-key -n M-z run-shell "nexus-ctl w"' in result
        assert len(result) == 1  # only one key, fully merged

    def test_empty_dirs_returns_empty(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        result = keymap_loader.load_keymap_cascade(str(d))
        assert result == []
