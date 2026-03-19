#!/usr/bin/env python3
# core/engine/orchestration/executor.py
"""
Nexus Execution Engine (V3)
===========================
Coordinates the execution of Capability-based Plans.
"""

import logging
import subprocess
from typing import cast

from ..capabilities.registry import REGISTRY
from ..capabilities.base import (
    CapabilityType,
    EditorCapability,
    ExplorerCapability,
    MultiplexerCapability,
)
from .planner import ExecutionPlan, WorkflowStep, OpType

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of a single step or full plan execution."""

    def __init__(self, success: bool, step_index: int = -1, error: str = ""):
        self.success = success
        self.step_index = step_index
        self.error = error

    def __bool__(self):
        return self.success

    def __repr__(self):
        status = "OK" if self.success else f"FAIL(step={self.step_index}: {self.error})"
        return f"ExecutionResult({status})"


class ExecutionCoordinator:
    """Orchestrates the lifecycle of a plan by invoking capabilities."""

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """Sequential execution of plan steps. Stops on first failure."""
        logger.debug(f"[Executor] Plan '{plan.intent}' — {len(plan.steps)} step(s)")

        for i, step in enumerate(plan.steps):
            logger.debug(
                f"[Executor]   step {i}: {step.op.name} via {step.capability} "
                f"(strategy={step.strategy})"
            )
            result = self._execute_step(i, step)
            if not result:
                logger.warning(f"[Executor] Step {i} failed: {result.error}")
                return result

        return ExecutionResult(success=True)

    # ------------------------------------------------------------------ #
    # Internal dispatch                                                    #
    # ------------------------------------------------------------------ #

    def _execute_step(self, index: int, step: WorkflowStep) -> ExecutionResult:
        try:
            if step.op == OpType.EDIT:
                return self._handle_edit(index, step)

            elif step.op == OpType.EXPLORE:
                return self._handle_explore(index, step)

            elif step.op in (OpType.EXECUTE, OpType.SPAWN):
                return self._handle_spawn(index, step)

            elif step.op == OpType.FOCUS:
                return self._handle_focus(index, step)

            elif step.op == OpType.RENDER:
                return self._handle_render(index, step)

            elif step.op == OpType.WAIT:
                # Placeholder — future: block until event bus emits signal
                return ExecutionResult(success=True, step_index=index)

            else:
                return ExecutionResult(False, index, f"Unhandled OpType: {step.op}")

        except Exception as exc:
            logger.exception(f"[Executor] Exception in step {index}")
            return ExecutionResult(False, index, str(exc))

    # ------------------------------------------------------------------ #
    # Handlers                                                             #
    # ------------------------------------------------------------------ #

    def _handle_edit(self, index: int, step: WorkflowStep) -> ExecutionResult:
        """Open a file in the registered editor capability."""
        cap = REGISTRY.get_best(CapabilityType.EDITOR)
        if not cap:
            return ExecutionResult(False, index, "No editor capability registered")
        editor = cast(EditorCapability, cap)

        path = step.params.get("path", "")
        if not path:
            return ExecutionResult(False, index, "EDIT step missing 'path' param")

        success = editor.open_resource(path)
        return ExecutionResult(bool(success), index, "" if success else "editor.open_resource failed")

    def _handle_explore(self, index: int, step: WorkflowStep) -> ExecutionResult:
        """Open a path in the registered explorer capability."""
        cap = REGISTRY.get_best(CapabilityType.EXPLORER)
        if not cap:
            return ExecutionResult(False, index, "No explorer capability registered")
        explorer = cast(ExplorerCapability, cap)

        path = step.params.get("path", ".")
        success = explorer.trigger_action("open", path)
        return ExecutionResult(bool(success), index, "" if success else "explorer.trigger_action failed")

    def _handle_spawn(self, index: int, step: WorkflowStep) -> ExecutionResult:
        """Spawn a command — exec_local runs inline; all others go via multiplexer."""
        command = step.params.get("command", "")
        if not command:
            return ExecutionResult(False, index, "SPAWN/EXECUTE step missing 'command' param")

        strategy = step.strategy

        # exec_local: run directly in the current process context
        if strategy == "exec_local":
            proc = subprocess.run(command, shell=True)
            if proc.returncode != 0:
                return ExecutionResult(False, index, f"exec_local exited {proc.returncode}")
            return ExecutionResult(True, step_index=index)

        # All multiplexer strategies require a mux capability
        cap = REGISTRY.get_best(CapabilityType.MULTIPLEXER)
        if not cap:
            return ExecutionResult(False, index, "No multiplexer capability registered")
        mux = cast(MultiplexerCapability, cap)

        name    = step.params.get("name", "nexus")
        session = step.params.get("session", "")

        if strategy == "stack_replace":
            # Send command into the first pane of the active window
            window = step.params.get("window", "")
            if window:
                panes = mux.list_panes(window)
                if panes:
                    mux.send_command(panes[0].handle, command)
                    return ExecutionResult(True, step_index=index)
            # No window specified or no panes — fall through to create_window
            handle = mux.create_window(session or "nexus", name)
            if handle:
                mux.send_command(handle, command)
        else:
            # stack_push (default): open a new window
            handle = mux.create_window(session or "nexus", name)
            if handle:
                mux.send_command(handle, command)

        return ExecutionResult(
            bool(handle), index,
            "" if handle else "mux.create_window returned empty handle"
        )

    def _handle_focus(self, index: int, step: WorkflowStep) -> ExecutionResult:
        """Select/focus an existing pane by handle."""
        cap = REGISTRY.get_best(CapabilityType.MULTIPLEXER)
        if not cap:
            return ExecutionResult(False, index, "No multiplexer capability registered")
        mux = cast(MultiplexerCapability, cap)

        pane_id = step.params.get("pane_id", "")
        if not pane_id:
            return ExecutionResult(False, index, "FOCUS step missing 'pane_id' param")

        mux.select_pane(pane_id)
        return ExecutionResult(True, step_index=index)

    def _handle_render(self, index: int, step: WorkflowStep) -> ExecutionResult:
        """Render/display content. Falls back to stdout if no renderer registered."""
        cap = REGISTRY.get_best(CapabilityType.RENDERER)

        if not cap:
            # Graceful fallback: print path or content to stdout
            output = step.params.get("path") or step.params.get("content", "")
            if output:
                print(output)
            return ExecutionResult(True, step_index=index)

        # Renderer capability exists — use it via generic trigger_action
        path    = step.params.get("path", "")
        content = step.params.get("content", "")
        payload = path or content
        success = cap.is_available()  # placeholder until RendererCapability ABC is defined
        logger.debug(f"[Executor] Renderer available={success}, payload={payload!r}")
        return ExecutionResult(success, index, "" if success else "renderer not available")
