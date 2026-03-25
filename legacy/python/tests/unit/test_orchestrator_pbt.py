#!/usr/bin/env python3
# tests/unit/test_orchestrator_pbt.py
import sys
import json
import pytest
from pathlib import Path
from typing import List, Dict, Any
from hypothesis import given, strategies as st, settings

# Path Setup
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "core/engine/state"))

from engine.capabilities.adapters.multiplexer.null import NullAdapter
from engine.orchestration.workspace import WorkspaceOrchestrator

# ── Strategies ───────────────────────────────────────────────────────────────

def leaf_pane():
    return st.fixed_dictionaries({
        "id": st.text(min_size=1, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        "command": st.text(min_size=1, alphabet=st.characters(whitelist_categories=('Ps', 'Pe', 'Lu', 'Ll', 'Nd', 'Pd', 'Zs')))
    })

@st.composite
def composition_layout(draw, depth=0):
    if depth > 2 or draw(st.booleans()):
        return draw(leaf_pane())
    
    return draw(st.fixed_dictionaries({
        "type": st.sampled_from(["hsplit", "vsplit"]),
        "panes": st.lists(composition_layout(depth + 1), min_size=2, max_size=3)
    }))

@st.composite
def composition(draw):
    layout = draw(composition_layout())
    return {
        "name": "pbt_test",
        "layout": layout
    }

# ── Helpers ───────────────────────────────────────────────────────────────────

def count_leaves(layout: Dict[str, Any]) -> int:
    if "panes" not in layout:
        return 1
    return sum(count_leaves(p) for p in layout["panes"])

def make_orchestrator(nexus_home: Path, project_root: Path, pane_count: int = 1) -> tuple:
    null = NullAdapter(initial_pane_count=pane_count)
    orch = WorkspaceOrchestrator(
        nexus_home=nexus_home,
        project_root=project_root,
        multiplexer=null,
    )
    return orch, null

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_p1_pane_count_invariant(mocker):
    """
    Invariant P1: After apply_composition, the physical pane count 
    in tmux must EXACTLY equal the leaf node count in the JSON.
    """
    @settings(deadline=None, max_examples=50)
    @given(comp_data=composition())
    def run_test(comp_data):
        expected_leaves = count_leaves(comp_data["layout"])
        session = "null_session:0"
        orch, null = make_orchestrator(PROJECT_ROOT, PROJECT_ROOT, pane_count=1)
        
        mocker.patch.object(orch, "_resolve_composition", return_value=comp_data)
        orch.apply_composition("dummy", session)
        
        actual_panes = null.list_panes(session)
        assert len(actual_panes) == expected_leaves, (
            f"P1 VIOLATED: Expected {expected_leaves} panes, got {len(actual_panes)}.\n"
            f"Layout: {json.dumps(comp_data, indent=2)}\n"
            f"Debugger Dump:\n{null.dump()}"
        )
    
    run_test()

def test_p2_full_identity_binding(mocker):
    """
    Invariant P2: Every pane must have a non-empty @nexus_stack_id.
    """
    @settings(deadline=None, max_examples=50)
    @given(comp_data=composition())
    def run_test(comp_data):
        session = "null_session:0"
        orch, null = make_orchestrator(PROJECT_ROOT, PROJECT_ROOT, pane_count=1)
        
        mocker.patch.object(orch, "_resolve_composition", return_value=comp_data)
        orch.apply_composition("dummy", session)
        
        panes = null.list_panes(session)
        for p in panes:
            assert p.stack_id is not None, f"Pane {p.handle} is an orphan (no stack_id)"
            assert len(p.stack_id) > 0, f"Pane {p.handle} has empty stack_id"

    run_test()

def test_p3_command_delivery(mocker):
    """
    Invariant P3: Every pane must receive its command.
    """
    @settings(deadline=None, max_examples=50)
    @given(comp_data=composition())
    def run_test(comp_data):
        session = "null_session:0"
        orch, null = make_orchestrator(PROJECT_ROOT, PROJECT_ROOT, pane_count=1)
        
        mocker.patch.object(orch, "_resolve_composition", return_value=comp_data)
        orch.apply_composition("dummy", session)
        
        panes = null.list_panes(session)
        for p in panes:
            assert p.handle in null.commands_sent, f"Pane {p.handle} never received a command"

    run_test()
