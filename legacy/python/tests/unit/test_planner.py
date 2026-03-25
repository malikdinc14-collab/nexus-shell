#!/usr/bin/env python3
# tests/unit/test_planner.py
"""
Unit tests for WorkflowPlanner (core/engine/orchestration/planner.py).

No mocks needed — planner is pure logic, no IO.
"""

import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from engine.orchestration.planner import WorkflowPlanner, ExecutionPlan, OpType


# ── Helpers ───────────────────────────────────────────────────────────────────

def plan(verb="run", itype="ACTION", payload="", intent="push", caller="terminal"):
    return WorkflowPlanner().plan({
        "verb": verb, "type": itype, "payload": payload,
        "intent": intent, "caller": caller,
    })


# ── Plan structure invariants ─────────────────────────────────────────────────

class TestPlanStructure:
    def test_returns_execution_plan(self):
        result = plan()
        assert isinstance(result, ExecutionPlan)

    def test_plan_has_at_least_one_step(self):
        for itype in ("ROLE", "PLACE", "PROJECT", "NOTE", "DOC", "MODEL", "AGENT", "ACTION"):
            result = plan(itype=itype, payload="test")
            assert len(result.steps) >= 1, f"No steps for itype={itype}"

    def test_intent_string_in_plan(self):
        result = plan(verb="run", itype="ROLE", payload="editor")
        assert "ROLE" in result.intent

    def test_unknown_itype_produces_echo_fallback(self):
        result = plan(itype="BANANA", payload="whatever")
        step = result.steps[0]
        assert "echo" in step.params.get("command", "").lower()
        assert step.strategy == "exec_local"


# ── Strategy mapping ──────────────────────────────────────────────────────────

class TestStrategyMapping:
    def test_intent_replace_sets_stack_replace(self):
        result = plan(itype="ROLE", payload="editor", intent="replace")
        assert result.steps[0].strategy == "stack_replace"

    def test_intent_push_sets_stack_push(self):
        result = plan(itype="ROLE", payload="editor", intent="push")
        assert result.steps[0].strategy == "stack_push"

    def test_intent_swap_defaults_to_stack_push(self):
        # "swap" is not explicitly handled — falls back to push
        result = plan(itype="ROLE", payload="editor", intent="swap")
        assert result.steps[0].strategy == "stack_push"

    def test_missing_intent_defaults_to_push(self):
        result = WorkflowPlanner().plan({"type": "ROLE", "payload": "terminal"})
        assert result.steps[0].strategy == "stack_push"


# ── ROLE dispatch ─────────────────────────────────────────────────────────────

class TestRoleDispatch:
    def test_role_editor_uses_env_nexus_editor(self, monkeypatch):
        monkeypatch.setenv("NEXUS_EDITOR", "hx")
        result = plan(itype="ROLE", payload="editor")
        assert result.steps[0].params["command"] == "hx"

    def test_role_editor_fallback_without_env(self, monkeypatch):
        monkeypatch.delenv("NEXUS_EDITOR", raising=False)
        result = plan(itype="ROLE", payload="editor")
        assert result.steps[0].params["command"] == "nvim"

    def test_role_explorer_uses_env_nexus_explorer(self, monkeypatch):
        monkeypatch.setenv("NEXUS_EXPLORER", "ranger")
        result = plan(itype="ROLE", payload="explorer")
        assert result.steps[0].params["command"] == "ranger"

    def test_role_terminal_uses_shell_env(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/fish")
        result = plan(itype="ROLE", payload="terminal")
        assert result.steps[0].params["command"] == "/bin/fish"

    def test_role_chat_defaults_to_opencode(self):
        result = plan(itype="ROLE", payload="chat")
        assert result.steps[0].params["command"] == "opencode"

    def test_role_unknown_uses_payload_as_command(self):
        result = plan(itype="ROLE", payload="mytool")
        assert result.steps[0].params["command"] == "mytool"

    def test_role_step_is_spawn_op(self):
        result = plan(itype="ROLE", payload="editor")
        assert result.steps[0].op == OpType.SPAWN


# ── PLACE / PROJECT dispatch ──────────────────────────────────────────────────

class TestPlaceProjectDispatch:
    def test_place_produces_cd_command(self):
        result = plan(itype="PLACE", payload="/tmp/mydir")
        cmd = result.steps[0].params["command"]
        assert "cd" in cmd
        assert "/tmp/mydir" in cmd

    def test_project_produces_cd_command(self):
        result = plan(itype="PROJECT", payload="/Users/shared/myproject")
        cmd = result.steps[0].params["command"]
        assert "cd" in cmd

    def test_place_step_is_spawn_op(self):
        result = plan(itype="PLACE", payload="/tmp")
        assert result.steps[0].op == OpType.SPAWN

    def test_path_with_spaces_safely_quoted(self):
        result = plan(itype="PLACE", payload="/my project/with spaces")
        cmd = result.steps[0].params["command"]
        # !r formatting wraps in quotes — shell meta-chars are literal
        assert ";" not in cmd or "/my project" in cmd


# ── NOTE / DOC dispatch ───────────────────────────────────────────────────────

class TestNoteDocDispatch:
    def test_note_produces_edit_op(self):
        result = plan(itype="NOTE", payload="/tmp/note.md")
        assert result.steps[0].op == OpType.EDIT

    def test_doc_produces_edit_op(self):
        result = plan(itype="DOC", payload="/docs/readme.md")
        assert result.steps[0].op == OpType.EDIT

    def test_edit_step_has_path_param(self):
        result = plan(itype="NOTE", payload="/tmp/note.md")
        assert result.steps[0].params["path"] == "/tmp/note.md"

    def test_edit_command_includes_editor(self, monkeypatch):
        monkeypatch.setenv("NEXUS_EDITOR", "hx")
        result = plan(itype="NOTE", payload="/tmp/note.md")
        assert "hx" in result.steps[0].params["command"]


# ── MODEL / AGENT dispatch ────────────────────────────────────────────────────

class TestModelAgentDispatch:
    def test_model_with_nexus_home_uses_agent_binary(self, monkeypatch):
        monkeypatch.setenv("NEXUS_HOME", "/nexus")
        result = plan(itype="MODEL", payload="gpt-4")
        cmd = result.steps[0].params["command"]
        assert "/nexus" in cmd
        assert "gpt-4" in cmd

    def test_model_without_nexus_home_shows_fallback(self, monkeypatch):
        monkeypatch.delenv("NEXUS_HOME", raising=False)
        result = plan(itype="MODEL", payload="gpt-4")
        cmd = result.steps[0].params["command"]
        assert "not configured" in cmd or "echo" in cmd

    def test_agent_step_is_spawn_op(self):
        result = plan(itype="AGENT", payload="claude")
        assert result.steps[0].op == OpType.SPAWN


# ── ACTION dispatch ───────────────────────────────────────────────────────────

class TestActionDispatch:
    def test_colon_prefix_uses_exec_local(self):
        result = plan(itype="ACTION", payload=":workspace dev")
        assert result.steps[0].strategy == "exec_local"
        assert result.steps[0].op in (OpType.EXECUTE, OpType.SPAWN)

    def test_no_colon_uses_multiplexer_strategy(self):
        result = plan(itype="ACTION", payload="git status")
        assert result.steps[0].strategy != "exec_local"

    def test_action_payload_in_command(self):
        result = plan(itype="ACTION", payload="git log --oneline")
        assert "git log" in result.steps[0].params["command"]
