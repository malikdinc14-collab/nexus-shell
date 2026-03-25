#!/usr/bin/env python3
# tests/unit/test_executor.py
"""
Unit tests for ExecutionCoordinator (core/engine/orchestration/executor.py).

Strategy: REGISTRY is a module-level singleton — patch get_best per test.
No live tmux, daemon, or filesystem access required.
"""

import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from engine.orchestration.executor import ExecutionCoordinator, ExecutionResult
from engine.orchestration.planner import ExecutionPlan, WorkflowStep, OpType
from engine.capabilities.base import CapabilityType, PaneInfo


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_plan(*steps, intent="test") -> ExecutionPlan:
    return ExecutionPlan(intent=intent, steps=list(steps))


def edit_step(path="file.py", **kw) -> WorkflowStep:
    return WorkflowStep(op=OpType.EDIT, capability="Editor",
                        params={"path": path}, **kw)


def explore_step(path="/tmp") -> WorkflowStep:
    return WorkflowStep(op=OpType.EXPLORE, capability="Explorer",
                        params={"path": path})


def spawn_step(cmd="echo hi", strategy="stack_push", **extra) -> WorkflowStep:
    return WorkflowStep(op=OpType.SPAWN, capability="Multiplexer",
                        params={"command": cmd, **extra}, strategy=strategy)


def execute_step(cmd="echo hi", strategy="exec_local") -> WorkflowStep:
    return WorkflowStep(op=OpType.EXECUTE, capability="Executor",
                        params={"command": cmd}, strategy=strategy)


def focus_step(pane_id="%1") -> WorkflowStep:
    return WorkflowStep(op=OpType.FOCUS, capability="Multiplexer",
                        params={"pane_id": pane_id})


def render_step(path="README.md") -> WorkflowStep:
    return WorkflowStep(op=OpType.RENDER, capability="Renderer",
                        params={"path": path})


def wait_step() -> WorkflowStep:
    return WorkflowStep(op=OpType.WAIT, capability="", params={})


# ── ExecutionResult ───────────────────────────────────────────────────────────

class TestExecutionResult:
    def test_success_is_truthy(self):
        assert ExecutionResult(success=True)

    def test_failure_is_falsy(self):
        assert not ExecutionResult(success=False)

    def test_repr_ok(self):
        r = ExecutionResult(success=True)
        assert "OK" in repr(r)

    def test_repr_fail_includes_step_and_error(self):
        r = ExecutionResult(success=False, step_index=2, error="boom")
        assert "step=2" in repr(r)
        assert "boom" in repr(r)

    def test_default_step_index(self):
        assert ExecutionResult(success=True).step_index == -1


# ── Empty / trivial plans ─────────────────────────────────────────────────────

class TestEmptyAndTrivialPlans:
    def test_empty_plan_returns_success(self):
        coord = ExecutionCoordinator()
        result = coord.execute(make_plan())
        assert result.success

    def test_wait_step_returns_success(self):
        coord = ExecutionCoordinator()
        result = coord.execute(make_plan(wait_step()))
        assert result.success

    def test_unknown_optype_returns_failure(self):
        coord = ExecutionCoordinator()
        step = WorkflowStep(op=MagicMock(spec=OpType), capability="",
                            params={}, strategy="exec_local")
        # Force the op to not match any known case
        step.op = "UNKNOWN_OP"
        result = coord._execute_step(0, step)
        assert not result

    def test_exception_in_step_returns_failure_not_crash(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_reg.get_best.side_effect = RuntimeError("registry exploded")
            result = coord.execute(make_plan(edit_step()))
        assert not result
        assert "registry exploded" in result.error


# ── Sequential halt ───────────────────────────────────────────────────────────

class TestSequentialHalt:
    def test_halts_at_first_failing_step(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_reg.get_best.return_value = None   # no editor → step 0 fails
            result = coord.execute(make_plan(edit_step(), wait_step()))
        assert not result
        assert result.step_index == 0

    def test_second_step_not_called_after_first_fails(self):
        coord = ExecutionCoordinator()
        called = []

        def track_step(i, step):
            called.append(i)
            return ExecutionResult(False, i, "forced fail")

        coord._execute_step = track_step
        coord.execute(make_plan(edit_step(), wait_step(), wait_step()))
        assert called == [0]

    def test_all_steps_run_when_all_succeed(self):
        coord = ExecutionCoordinator()
        called = []

        def track_step(i, step):
            called.append(i)
            return ExecutionResult(True, i)

        coord._execute_step = track_step
        result = coord.execute(make_plan(wait_step(), wait_step(), wait_step()))
        assert called == [0, 1, 2]
        assert result.success


# ── EDIT handler ──────────────────────────────────────────────────────────────

class TestHandleEdit:
    def test_no_editor_capability_returns_failure(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_reg.get_best.return_value = None
            result = coord._handle_edit(0, edit_step())
        assert not result
        assert "No editor" in result.error

    def test_missing_path_param_returns_failure(self):
        coord = ExecutionCoordinator()
        step = WorkflowStep(op=OpType.EDIT, capability="Editor", params={})
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_editor = MagicMock()
            mock_reg.get_best.return_value = mock_editor
            result = coord._handle_edit(0, step)
        assert not result
        assert "path" in result.error

    def test_open_resource_success(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_editor = MagicMock()
            mock_editor.open_resource.return_value = True
            mock_reg.get_best.return_value = mock_editor
            result = coord._handle_edit(0, edit_step("myfile.py"))
        assert result.success
        mock_editor.open_resource.assert_called_once_with("myfile.py")

    def test_open_resource_failure_propagates(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_editor = MagicMock()
            mock_editor.open_resource.return_value = False
            mock_reg.get_best.return_value = mock_editor
            result = coord._handle_edit(0, edit_step())
        assert not result


# ── EXPLORE handler ───────────────────────────────────────────────────────────

class TestHandleExplore:
    def test_no_explorer_returns_failure(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_reg.get_best.return_value = None
            result = coord._handle_explore(0, explore_step())
        assert not result
        assert "No explorer" in result.error

    def test_trigger_action_called_with_path(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_exp = MagicMock()
            mock_exp.trigger_action.return_value = True
            mock_reg.get_best.return_value = mock_exp
            result = coord._handle_explore(0, explore_step("/home/user"))
        assert result.success
        mock_exp.trigger_action.assert_called_once_with("open", "/home/user")

    def test_missing_path_defaults_to_dot(self):
        coord = ExecutionCoordinator()
        step = WorkflowStep(op=OpType.EXPLORE, capability="Explorer", params={})
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_exp = MagicMock()
            mock_exp.trigger_action.return_value = True
            mock_reg.get_best.return_value = mock_exp
            coord._handle_explore(0, step)
        mock_exp.trigger_action.assert_called_once_with("open", ".")


# ── SPAWN / EXECUTE handler ───────────────────────────────────────────────────

class TestHandleSpawn:
    def test_missing_command_returns_failure(self):
        coord = ExecutionCoordinator()
        step = WorkflowStep(op=OpType.SPAWN, capability="Multiplexer", params={})
        result = coord._handle_spawn(0, step)
        assert not result
        assert "command" in result.error

    def test_exec_local_success(self):
        coord = ExecutionCoordinator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = coord._handle_spawn(0, spawn_step("true", strategy="exec_local"))
        assert result.success

    def test_exec_local_nonzero_exit_returns_failure(self):
        coord = ExecutionCoordinator()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = coord._handle_spawn(0, spawn_step("false", strategy="exec_local"))
        assert not result

    def test_stack_push_no_mux_returns_failure(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_reg.get_best.return_value = None
            result = coord._handle_spawn(0, spawn_step(strategy="stack_push"))
        assert not result
        assert "No multiplexer" in result.error

    def test_stack_push_creates_window_and_sends_command(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_mux = MagicMock()
            mock_mux.create_window.return_value = "%10"
            mock_reg.get_best.return_value = mock_mux
            result = coord._handle_spawn(0, spawn_step("nvim", strategy="stack_push"))
        assert result.success
        mock_mux.create_window.assert_called_once()
        mock_mux.send_command.assert_called_once_with("%10", "nvim")

    def test_stack_replace_uses_existing_pane_when_available(self):
        coord = ExecutionCoordinator()
        pane = PaneInfo(handle="%5", index=0, width=80, height=24, stack_id="editor")
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_mux = MagicMock()
            mock_mux.list_panes.return_value = [pane]
            mock_reg.get_best.return_value = mock_mux
            step = spawn_step("nvim", strategy="stack_replace", window="nexus:0")
            result = coord._handle_spawn(0, step)
        assert result.success
        mock_mux.send_command.assert_called_once_with("%5", "nvim")


# ── FOCUS handler ─────────────────────────────────────────────────────────────

class TestHandleFocus:
    def test_no_mux_returns_failure(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_reg.get_best.return_value = None
            result = coord._handle_focus(0, focus_step())
        assert not result

    def test_missing_pane_id_returns_failure(self):
        coord = ExecutionCoordinator()
        step = WorkflowStep(op=OpType.FOCUS, capability="Multiplexer", params={})
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_reg.get_best.return_value = MagicMock()
            result = coord._handle_focus(0, step)
        assert not result
        assert "pane_id" in result.error

    def test_select_pane_called_with_handle(self):
        coord = ExecutionCoordinator()
        with patch("engine.orchestration.executor.REGISTRY") as mock_reg:
            mock_mux = MagicMock()
            mock_reg.get_best.return_value = mock_mux
            result = coord._handle_focus(0, focus_step("%7"))
        assert result.success
        mock_mux.select_pane.assert_called_once_with("%7")


# ── RENDER handler ────────────────────────────────────────────────────────────

class TestHandleRender:
    def test_render_falls_back_to_stdout(self, capsys):
        coord = ExecutionCoordinator()
        step = render_step("README.md")
        result = coord._execute_step(0, step)
        assert result.success
        captured = capsys.readouterr()
        assert "README.md" in captured.out

    def test_render_with_content_param(self, capsys):
        coord = ExecutionCoordinator()
        step = WorkflowStep(op=OpType.RENDER, capability="Renderer",
                            params={"content": "hello world"})
        result = coord._execute_step(0, step)
        assert result.success
        captured = capsys.readouterr()
        assert "hello world" in captured.out
