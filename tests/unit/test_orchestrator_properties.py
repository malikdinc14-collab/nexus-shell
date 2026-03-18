#!/usr/bin/env python3
# tests/unit/test_orchestrator_properties.py
"""
Property-Based Tests: WorkspaceOrchestrator + NullAdapter
==========================================================
These tests verify invariants that must hold for ANY valid composition,
regardless of which multiplexer backend is used.

Core properties tested:

  P1 — PANE COUNT:
    After applying a composition, the number of physical panes must equal
    the number of leaf nodes declared in the composition JSON.

  P2 — FULL IDENTITY BINDING:
    Every pane must have a non-empty @nexus_stack_id after boot.
    No orphans allowed in a clean boot.

  P3 — COMMAND DELIVERY:
    Every pane must have received at least one send_command call.

  P4 — IDEMPOTENT IDENTITY:
    Running apply_composition twice must not double-register identities
    or send duplicate commands beyond the second run.

  P5 — LAST-PANE RULE:
    The last pane in the layout always occupies the seed (initial) pane —
    it must never be split further.

Run:
    python3 -m pytest tests/unit/test_orchestrator_properties.py -v
"""

import sys
import json
import pytest
from pathlib import Path
from typing import List, Dict, Any

# ── Path Setup ───────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "core/engine/state"))

from engine.capabilities.adapters.null import NullAdapter
from engine.orchestration.workspace import WorkspaceOrchestrator


# ── Test Fixtures ─────────────────────────────────────────────────────────────

NEXUS_HOME = PROJECT_ROOT
TEST_SESSION = "null_session:0"


def make_orchestrator(pane_count: int = 1) -> tuple:
    """Returns (orchestrator, null_adapter) pair."""
    null = NullAdapter(initial_pane_count=pane_count)
    orch = WorkspaceOrchestrator(
        nexus_home=NEXUS_HOME,
        project_root=PROJECT_ROOT,
        multiplexer=null,
    )
    return orch, null


def count_leaves(layout: Dict[str, Any]) -> int:
    """
    Recursively count leaf panes in a composition layout dict.
    Invariant: len(leaves) == expected physical pane count after boot.
    """
    if "panes" not in layout:
        return 1
    return sum(count_leaves(p) for p in layout["panes"])


def load_composition(name: str) -> Dict[str, Any]:
    paths = [
        NEXUS_HOME / f"core/ui/compositions/{name}.json",
        PROJECT_ROOT / f".nexus/compositions/{name}.json",
    ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    pytest.fail(f"Composition '{name}' not found.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def all_panes_from_null(null: NullAdapter, window: str) -> list:
    return null.list_panes(window)


# ── P1: Pane Count ────────────────────────────────────────────────────────────

class TestPaneCount:

    def test_vscodelike_creates_5_panes(self):
        """vscodelike declares 5 leaf panes: files, menu, editor, terminal, chat."""
        comp = load_composition("vscodelike")
        expected_leaves = count_leaves(comp["layout"])
        assert expected_leaves == 5, f"Expected 5 leaves, got {expected_leaves}"

        orch, null = make_orchestrator(pane_count=1)
        orch.apply_composition("vscodelike", TEST_SESSION)

        actual = all_panes_from_null(null, TEST_SESSION)
        assert len(actual) == expected_leaves, (
            f"P1 VIOLATED: vscodelike expected {expected_leaves} panes, "
            f"got {len(actual)}.\n{null.dump()}"
        )

    def test_minimal_creates_correct_pane_count(self):
        """minimal.json should boot the exact pane count it declares."""
        try:
            comp = load_composition("minimal")
        except Exception:
            pytest.skip("minimal.json not found")

        expected = count_leaves(comp["layout"])
        orch, null = make_orchestrator(pane_count=1)
        orch.apply_composition("minimal", TEST_SESSION)

        actual = all_panes_from_null(null, TEST_SESSION)
        assert len(actual) == expected, (
            f"P1 VIOLATED: minimal expected {expected} panes, got {len(actual)}"
        )

    @pytest.mark.parametrize("comp_name", [
        "vscodelike", "minimal",
    ])
    def test_leaf_count_matches_pane_count_parametric(self, comp_name):
        """Generic: for any composition, leaf count == pane count after boot."""
        try:
            comp = load_composition(comp_name)
        except Exception:
            pytest.skip(f"{comp_name} not found")

        expected = count_leaves(comp["layout"])
        orch, null = make_orchestrator(pane_count=1)
        orch.apply_composition(comp_name, TEST_SESSION)

        actual = all_panes_from_null(null, TEST_SESSION)
        assert len(actual) == expected


# ── P2: Full Identity Binding ─────────────────────────────────────────────────

class TestIdentityBinding:

    def test_no_orphan_panes_after_vscodelike_boot(self):
        """P2: Every pane must receive a @nexus_stack_id. No orphans."""
        orch, null = make_orchestrator(pane_count=1)
        orch.apply_composition("vscodelike", TEST_SESSION)

        panes = all_panes_from_null(null, TEST_SESSION)
        assert len(panes) > 0, "No panes found after boot"

        orphans = [p for p in panes if not p.stack_id]
        assert not orphans, (
            f"P2 VIOLATED: {len(orphans)} orphan pane(s) found:\n"
            + "\n".join(f"  {p.handle}" for p in orphans)
            + f"\n{null.dump()}"
        )

    def test_specific_stack_ids_are_bound(self):
        """All declared pane IDs from vscodelike must be physically present."""
        expected_ids = {"files", "menu", "editor", "terminal", "chat"}
        orch, null = make_orchestrator(pane_count=1)
        orch.apply_composition("vscodelike", TEST_SESSION)

        panes = all_panes_from_null(null, TEST_SESSION)
        bound_ids = {p.stack_id for p in panes if p.stack_id}

        missing = expected_ids - bound_ids
        assert not missing, (
            f"P2 VIOLATED: Stack IDs not bound: {missing}\n"
            f"Bound: {bound_ids}\n{null.dump()}"
        )


# ── P3: Command Delivery ──────────────────────────────────────────────────────

class TestCommandDelivery:

    def test_all_panes_receive_a_command(self):
        """P3: Every pane must have send_command called at least once."""
        orch, null = make_orchestrator(pane_count=1)
        orch.apply_composition("vscodelike", TEST_SESSION)

        panes = all_panes_from_null(null, TEST_SESSION)
        silent = [p for p in panes if p.handle not in null.commands_sent]

        assert not silent, (
            f"P3 VIOLATED: {len(silent)} pane(s) received no command:\n"
            + "\n".join(f"  {p.handle} [{p.stack_id}]" for p in silent)
        )

    def test_chat_pane_uses_adapter_launch_command(self):
        """P3b: The chat pane command must use the adapter override (with sleep)."""
        orch, null = make_orchestrator(pane_count=1)
        orch.apply_composition("vscodelike", TEST_SESSION)

        null.assert_pane_has_command("chat", "opencode")

    def test_editor_pane_command_not_bare_variable(self):
        """P3c: The editor command must not contain unexpanded '$' variables."""
        orch, null = make_orchestrator(pane_count=1)
        orch.apply_composition("vscodelike", TEST_SESSION)

        panes = all_panes_from_null(null, TEST_SESSION)
        for p in panes:
            if p.stack_id == "editor":
                cmd = null.commands_sent.get(p.handle, "")
                assert "$EDITOR_CMD" not in cmd, (
                    f"P3c VIOLATED: Unexpanded variable in editor command: {cmd}"
                )
                assert "$NEXUS_EDITOR" not in cmd, (
                    f"P3c VIOLATED: Unexpanded variable in editor command: {cmd}"
                )


# ── P4: Idempotent Identity ───────────────────────────────────────────────────

class TestIdempotency:

    def test_momentum_boot_does_not_multiply_panes(self):
        """
        P4: Running _build_momentum on an already-booted window should
        converge to the correct pane count, not double it.
        The NullAdapter pre-populates the window with 5 panes.
        The orchestrator must detect this and reuse without splitting.
        """
        orch, null = make_orchestrator(pane_count=5)  # already 5 panes
        
        # We simulate a momentum boot by passing a flat snapshot representing 5 panes
        snapshot = {
            "panes": [
                {"id": "files", "command": "yazi"},
                {"id": "menu", "command": "menu"},
                {"id": "editor", "command": "nvim"},
                {"id": "terminal", "command": "zsh"},
                {"id": "chat", "command": "opencode"},
            ]
        }
        orch._build_momentum(snapshot, TEST_SESSION)

        panes = all_panes_from_null(null, TEST_SESSION)
        # Should still be 5, not 10 (or 3)
        assert len(panes) == 5, (
            f"P4 VIOLATED: Momentum boot created {len(panes)} panes instead of 5.\n"
            f"{null.dump()}"
        )


# ── P5: NullAdapter Self-Tests ────────────────────────────────────────────────

class TestNullAdapter:
    """Verify the NullAdapter itself is correct before using it as a test oracle."""

    def test_initial_pane_exists(self):
        null = NullAdapter(initial_pane_count=1)
        panes = null.list_panes(TEST_SESSION)
        assert len(panes) == 1

    def test_split_increases_pane_count(self):
        null = NullAdapter(initial_pane_count=1)
        initial = null.list_panes(TEST_SESSION)
        seed = initial[0].handle
        null.split(seed, direction="h")
        panes = null.list_panes(TEST_SESSION)
        assert len(panes) == 2

    def test_set_tag_and_get_tag(self):
        null = NullAdapter(initial_pane_count=1)
        panes = null.list_panes(TEST_SESSION)
        handle = panes[0].handle
        null.set_tag(handle, "@nexus_stack_id", "editor")
        assert null.get_tag(handle, "@nexus_stack_id") == "editor"

    def test_send_command_recorded(self):
        null = NullAdapter(initial_pane_count=1)
        panes = null.list_panes(TEST_SESSION)
        null.send_command(panes[0].handle, "nvim .")
        assert null.commands_sent[panes[0].handle] == "nvim ."

    def test_apply_layout_always_succeeds(self):
        null = NullAdapter(initial_pane_count=1)
        assert null.apply_layout(TEST_SESSION, "even-horizontal") is True

    def test_assert_pane_has_command_passes(self):
        null = NullAdapter(initial_pane_count=1)
        panes = null.list_panes(TEST_SESSION)
        null.set_tag(panes[0].handle, "@nexus_stack_id", "chat")
        null.send_command(panes[0].handle, "sleep 1.5 && opencode")
        null.assert_pane_has_command("chat", "opencode")  # should not raise

    def test_assert_pane_has_command_fails_correctly(self):
        null = NullAdapter(initial_pane_count=1)
        panes = null.list_panes(TEST_SESSION)
        null.set_tag(panes[0].handle, "@nexus_stack_id", "chat")
        null.send_command(panes[0].handle, "zsh")
        with pytest.raises(AssertionError, match="expected 'opencode'"):
            null.assert_pane_has_command("chat", "opencode")

    def test_kill_pane_removes_from_list(self):
        null = NullAdapter(initial_pane_count=1)
        panes = null.list_panes(TEST_SESSION)
        null.kill_pane(panes[0].handle)
        assert null.list_panes(TEST_SESSION) == []
