#!/usr/bin/env python3
# tests/unit/test_switcher.py
"""
Unit tests for switcher.py (core/engine/api/switcher.py).

All subprocess and tmux calls are mocked — no live tmux session needed.
"""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core/engine/api"))
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from switcher import (
    fzf_pick,
    tmux_query,
    switch_global,
    switch_terminal,
)


# ── fzf_pick ──────────────────────────────────────────────────────────────────

class TestFzfPick:
    def test_empty_list_returns_none(self):
        assert fzf_pick([], "header") is None

    def test_fzf_tmux_not_found_falls_back_to_fzf(self):
        def fake_run(cmd, *a, **kw):
            if cmd[0] == "fzf-tmux":
                raise FileNotFoundError
            result = MagicMock()
            result.stdout = "1: file.py\n"
            return result

        with patch("subprocess.run", side_effect=fake_run):
            result = fzf_pick(["1: file.py"], "header")
        assert result == "1: file.py"

    def test_fzf_not_found_returns_none(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = fzf_pick(["item"], "header")
        assert result is None

    def test_fzf_empty_output_returns_none(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            result = fzf_pick(["item"], "header")
        assert result is None

    def test_fzf_returns_selected_item(self):
        mock_result = MagicMock()
        mock_result.stdout = "2: main.py"
        with patch("subprocess.run", return_value=mock_result):
            result = fzf_pick(["1: file.py", "2: main.py"], "header")
        assert result == "2: main.py"


# ── tmux_query ────────────────────────────────────────────────────────────────

class TestTmuxQuery:
    def test_returns_empty_string_when_tmux_not_found(self):
        with patch("subprocess.check_output", side_effect=FileNotFoundError):
            result = tmux_query("#{pane_id}")
        assert result == ""

    def test_returns_empty_string_on_called_process_error(self):
        import subprocess
        with patch("subprocess.check_output",
                   side_effect=subprocess.CalledProcessError(1, "tmux")):
            result = tmux_query("#{pane_id}")
        assert result == ""

    def test_returns_stripped_output(self):
        with patch("subprocess.check_output", return_value=b"  %5  \n"):
            result = tmux_query("#{pane_id}")
        assert result == "%5"


# ── switch_global ─────────────────────────────────────────────────────────────

class TestSwitchGlobal:
    def test_no_tmux_returns_silently(self):
        import subprocess
        with patch("subprocess.check_output",
                   side_effect=subprocess.CalledProcessError(1, "tmux")):
            # Should not raise
            switch_global("nexus_test")

    def test_no_windows_returns_silently(self):
        with patch("subprocess.check_output", return_value=b""):
            switch_global("nexus_test")

    def test_select_window_called_on_choice(self):
        with patch("subprocess.check_output",
                   return_value=b"0: workspace_0\n1: workspace_1\n"):
            mock_result = MagicMock()
            mock_result.stdout = "1: workspace_1"
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                with patch("switcher.fzf_pick", return_value="1: workspace_1"):
                    switch_global("nexus_test")
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "select-window" in cmd
            assert ":1" in cmd[-1]


# ── switch_terminal ───────────────────────────────────────────────────────────

class TestSwitchTerminal:
    def test_no_terminal_tabs_script_returns_silently(self, tmp_path):
        # Passing a nexus_home where terminal_tabs.sh doesn't exist
        switch_terminal("%5", str(tmp_path))  # Should not raise

    def test_terminal_tabs_error_returns_silently(self, tmp_path):
        import subprocess
        tabs_script = tmp_path / "core" / "terminal_tabs.sh"
        tabs_script.parent.mkdir(parents=True)
        tabs_script.touch()
        with patch("subprocess.check_output",
                   side_effect=subprocess.CalledProcessError(1, "terminal_tabs.sh")):
            switch_terminal("%5", str(tmp_path))

    def test_swap_pane_called_on_valid_choice(self, tmp_path):
        tabs_script = tmp_path / "core" / "terminal_tabs.sh"
        tabs_script.parent.mkdir(parents=True)
        tabs_script.touch()

        with patch("subprocess.check_output",
                   return_value=b"tab1 [%23]\ntab2 [%24]\n"):
            with patch("switcher.fzf_pick", return_value="tab2 [%24]"):
                with patch("subprocess.run") as mock_run:
                    switch_terminal("%5", str(tmp_path))

        # Should have called swap-pane and select-pane
        calls = [c[0][0] for c in mock_run.call_args_list]
        assert any("swap-pane" in c for c in calls)
        assert any("select-pane" in c for c in calls)
