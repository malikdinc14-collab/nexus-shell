#!/usr/bin/env python3
# tests/unit/test_nexus_ctl.py
"""
Unit tests for nexus-ctl CLI (core/engine/api/nexus_ctl.py).

Mocks IntentResolver and subprocess to avoid live process execution.
"""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core/engine/api"))
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from intent_resolver_legacy import parse_legacy, main, execute_plan


# ── parse_legacy ──────────────────────────────────────────────────────────────

class TestParseLegacy:
    def test_pipe_format_splits_type_and_data(self):
        verb, itype, payload = parse_legacy("ROLE|editor")
        assert verb == "run"
        assert itype == "ROLE"
        assert payload == "editor"

    def test_pipe_format_uppercases_type(self):
        _, itype, _ = parse_legacy("role|editor")
        assert itype == "ROLE"

    def test_pipe_format_strips_whitespace(self):
        _, itype, payload = parse_legacy("ROLE | editor ")
        assert itype == "ROLE"
        assert payload == "editor"

    def test_no_pipe_is_action(self):
        verb, itype, payload = parse_legacy("git status")
        assert itype == "ACTION"
        assert payload == "git status"

    def test_pipe_with_complex_data(self):
        _, itype, payload = parse_legacy("NOTE|/path/to/file.md")
        assert itype == "NOTE"
        assert payload == "/path/to/file.md"

    def test_multiple_pipes_splits_on_first(self):
        _, itype, payload = parse_legacy("ACTION|cmd|with|pipes")
        assert itype == "ACTION"
        assert payload == "cmd|with|pipes"


# ── main() arg parsing ────────────────────────────────────────────────────────

GOOD_PLAN = {"strategy": "stack_push", "role": "editor",
             "cmd": "nvim", "name": "editor"}


class TestMainArgParsing:
    def _run(self, argv, plan=GOOD_PLAN):
        with patch("intent_resolver_legacy.IntentResolver") as MockResolver:
            MockResolver.return_value.resolve.return_value = plan
            return main(argv)

    def test_legacy_single_arg_returns_json(self, capsys):
        rc = self._run(["ROLE|editor"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["strategy"] == "stack_push"

    def test_run_subcommand_three_args(self, capsys):
        rc = self._run(["run", "ROLE", "editor"])
        assert rc == 0

    def test_short_two_arg_format(self, capsys):
        rc = self._run(["ROLE", "editor"])
        assert rc == 0

    def test_no_args_returns_nonzero(self):
        with patch("intent_resolver_legacy.IntentResolver"):
            with pytest.raises(SystemExit) as exc_info:
                main([])
        assert exc_info.value.code != 0

    def test_intent_flag_passed_to_resolver(self):
        with patch("intent_resolver_legacy.IntentResolver") as MockResolver:
            MockResolver.return_value.resolve.return_value = GOOD_PLAN
            main(["ROLE", "editor", "--intent", "replace"])
            args = MockResolver.return_value.resolve.call_args
            assert "replace" in args[0]

    def test_caller_flag_passed_to_resolver(self):
        with patch("intent_resolver_legacy.IntentResolver") as MockResolver:
            MockResolver.return_value.resolve.return_value = GOOD_PLAN
            main(["ROLE", "editor", "--caller", "menu"])
            args = MockResolver.return_value.resolve.call_args
            assert "menu" in args[0]

    def test_resolver_exception_outputs_json_error(self, capsys):
        with patch("intent_resolver_legacy.IntentResolver") as MockResolver:
            MockResolver.return_value.resolve.side_effect = RuntimeError("oops")
            rc = main(["ROLE", "editor"])
        assert rc == 1
        out = json.loads(capsys.readouterr().out)
        assert "error" in out

    def test_empty_plan_outputs_json_error(self, capsys):
        with patch("intent_resolver_legacy.IntentResolver") as MockResolver:
            MockResolver.return_value.resolve.return_value = {}
            rc = main(["ROLE", "editor"])
        assert rc == 1


# ── execute_plan ──────────────────────────────────────────────────────────────

class TestExecutePlan:
    def _exec(self, plan, returncode=0):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=returncode)
            return execute_plan(plan, "/fake/nexus"), mock_run

    def test_stack_push_calls_stack_binary(self):
        plan = {"strategy": "stack_push", "role": "editor",
                "cmd": "nvim", "name": "editor"}
        rc, mock_run = self._exec(plan)
        assert rc == 0
        cmd = mock_run.call_args[0][0]
        assert "stack" in str(cmd)
        assert "push" in cmd

    def test_stack_switch_calls_switch_subcommand(self):
        plan = {"strategy": "stack_switch", "role": "editor",
                "cmd": "", "index": "2"}
        rc, mock_run = self._exec(plan)
        cmd = mock_run.call_args[0][0]
        assert "switch" in cmd

    def test_stack_replace_calls_replace_subcommand(self):
        plan = {"strategy": "stack_replace", "role": "terminal",
                "cmd": "zsh", "name": "terminal"}
        rc, mock_run = self._exec(plan)
        cmd = mock_run.call_args[0][0]
        assert "replace" in cmd

    def test_exec_local_runs_shell_command(self):
        plan = {"strategy": "exec_local", "role": "local",
                "cmd": "echo hi", "name": "local"}
        rc, mock_run = self._exec(plan)
        assert rc == 0
        # exec_local uses shell=True
        assert mock_run.call_args[1].get("shell") is True

    def test_unknown_strategy_falls_back_to_push(self):
        plan = {"strategy": "alien_strategy", "role": "x",
                "cmd": "x", "name": "x"}
        rc, mock_run = self._exec(plan)
        cmd = mock_run.call_args[0][0]
        assert "push" in cmd

    def test_file_not_found_returns_exit_1(self):
        plan = {"strategy": "stack_push", "role": "x", "cmd": "x", "name": "x"}
        with patch("subprocess.run", side_effect=FileNotFoundError("no binary")):
            rc = execute_plan(plan, "/fake/nexus")
        assert rc == 1

    def test_nonzero_returncode_propagates(self):
        plan = {"strategy": "stack_push", "role": "x", "cmd": "x", "name": "x"}
        rc, _ = self._exec(plan, returncode=42)
        assert rc == 42
