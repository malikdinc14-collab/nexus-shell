"""Tests for momentum extensions: stack persistence, deferred restore, geometry, session."""

import importlib
import importlib.util
import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load_module(name, rel_path):
    if name in sys.modules:
        return sys.modules[name]
    full = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

_stack_mod = _load_module("engine.stacks.stack", "core/engine/stacks/stack.py")
_reservoir_mod = _load_module("engine.stacks.reservoir", "core/engine/stacks/reservoir.py")
_manager_mod = _load_module("engine.stacks.manager", "core/engine/stacks/manager.py")
_persist_mod = _load_module(
    "engine.momentum.stack_persistence",
    "core/engine/momentum/stack_persistence.py",
)
_deferred_mod = _load_module(
    "engine.momentum.deferred_restore",
    "core/engine/momentum/deferred_restore.py",
)
_geometry_mod = _load_module(
    "engine.momentum.geometry",
    "core/engine/momentum/geometry.py",
)
_session_mod = _load_module(
    "engine.momentum.session",
    "core/engine/momentum/session.py",
)

Tab = _stack_mod.Tab
TabStack = _stack_mod.TabStack
StackManager = _manager_mod.StackManager
serialize_stacks = _persist_mod.serialize_stacks
deserialize_stacks = _persist_mod.deserialize_stacks
DeferredRestore = _deferred_mod.DeferredRestore
capture_geometry = _geometry_mod.capture_geometry
apply_geometry = _geometry_mod.apply_geometry
save_session = _session_mod.save_session
restore_session = _session_mod.restore_session
load_geometry = _session_mod.load_geometry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tab(**kwargs):
    defaults = dict(
        capability_type="terminal",
        adapter_name="zsh",
        command="zsh",
        cwd="/home/user",
        role="shell",
        env={"TERM": "xterm"},
        is_active=False,
    )
    defaults.update(kwargs)
    return Tab(**defaults)


def _populated_manager():
    mgr = StackManager()
    t1 = _make_tab(capability_type="editor", adapter_name="neovim", command="nvim", is_active=True)
    t2 = _make_tab(capability_type="terminal", adapter_name="zsh", command="zsh")
    mgr.push("%1", t1)
    mgr.push("%1", t2)
    t3 = _make_tab(capability_type="chat", adapter_name="opencode", command="opencode")
    mgr.push("%2", t3)
    return mgr


# ===========================================================================
# T050 — serialize / deserialize round-trip
# ===========================================================================

class TestStackPersistence:
    def test_serialize_returns_dict_per_pane(self):
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        assert "%1" in data
        assert "%2" in data

    def test_serialize_contains_tab_fields(self):
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        tab_data = data["%2"]["tabs"][0]
        for field in ("capability_type", "adapter_name", "command", "cwd", "role", "env", "is_active"):
            assert field in tab_data

    def test_serialize_excludes_tmux_pane_id(self):
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        tab_data = data["%1"]["tabs"][0]
        assert "tmux_pane_id" not in tab_data

    def test_serialize_preserves_active_index(self):
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        # After two pushes on %1, active_index should be 1
        assert data["%1"]["active_index"] == 1

    def test_serialize_empty_manager(self):
        mgr = StackManager()
        data = serialize_stacks(mgr)
        assert data == {}

    def test_deserialize_roundtrip(self):
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        mgr2 = StackManager()
        deserialize_stacks(data, mgr2)
        assert set(mgr2.all_stacks().keys()) == {"%1", "%2"}
        assert len(mgr2.get_stack("%1").tabs) == 2
        assert len(mgr2.get_stack("%2").tabs) == 1

    def test_deserialize_restores_tab_fields(self):
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        mgr2 = StackManager()
        deserialize_stacks(data, mgr2)
        tab = mgr2.get_stack("%2").tabs[0]
        assert tab.capability_type == "chat"
        assert tab.adapter_name == "opencode"
        assert tab.command == "opencode"

    def test_deserialize_assigns_pane_id(self):
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        mgr2 = StackManager()
        deserialize_stacks(data, mgr2)
        for tab in mgr2.get_stack("%1").tabs:
            assert tab.tmux_pane_id == "%1"

    def test_deserialize_preserves_env(self):
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        mgr2 = StackManager()
        deserialize_stacks(data, mgr2)
        tab = mgr2.get_stack("%1").tabs[0]
        assert tab.env == {"TERM": "xterm"}

    def test_deserialize_preserves_role(self):
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        mgr2 = StackManager()
        deserialize_stacks(data, mgr2)
        assert mgr2.get_stack("%1").tabs[0].role == "shell"

    def test_json_safe(self):
        """serialize_stacks output should be JSON-serializable."""
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        dumped = json.dumps(data)
        loaded = json.loads(dumped)
        assert loaded == data


# ===========================================================================
# T051 — DeferredRestore
# ===========================================================================

class TestDeferredRestore:
    def test_queue_and_apply(self):
        dr = DeferredRestore()
        tabs = [_make_tab(), _make_tab()]
        dr.queue_restore("%1", tabs)
        result = dr.apply_pending("%1")
        assert len(result) == 2
        # Once applied, pending is cleared
        assert dr.apply_pending("%1") == []

    def test_pending_count(self):
        dr = DeferredRestore()
        dr.queue_restore("%1", [_make_tab()])
        dr.queue_restore("%2", [_make_tab(), _make_tab()])
        assert dr.pending_count() == 3

    def test_pending_count_zero(self):
        dr = DeferredRestore()
        assert dr.pending_count() == 0

    def test_apply_pending_empty(self):
        dr = DeferredRestore()
        assert dr.apply_pending("%99") == []

    def test_queue_empty_list_is_noop(self):
        dr = DeferredRestore()
        dr.queue_restore("%1", [])
        assert dr.pending_count() == 0

    def test_multiple_queues_same_pane(self):
        dr = DeferredRestore()
        dr.queue_restore("%1", [_make_tab()])
        dr.queue_restore("%1", [_make_tab()])
        assert dr.pending_count() == 2
        result = dr.apply_pending("%1")
        assert len(result) == 2

    def test_pending_panes(self):
        dr = DeferredRestore()
        dr.queue_restore("%1", [_make_tab()])
        dr.queue_restore("%3", [_make_tab()])
        assert set(dr.pending_panes()) == {"%1", "%3"}

    def test_apply_removes_pane_from_pending(self):
        dr = DeferredRestore()
        dr.queue_restore("%1", [_make_tab()])
        dr.apply_pending("%1")
        assert "%1" not in dr.pending_panes()


# ===========================================================================
# T052 — geometry capture / apply
# ===========================================================================

class TestGeometry:
    def test_capture_basic(self):
        dims = {
            "%1": {"width": 80, "height": 24, "total_width": 160, "total_height": 48},
        }
        geo = capture_geometry(["%1"], dims)
        assert geo["%1"]["width_pct"] == pytest.approx(50.0)
        assert geo["%1"]["height_pct"] == pytest.approx(50.0)

    def test_capture_no_dimensions(self):
        geo = capture_geometry(["%1"])
        assert geo["%1"]["width_pct"] == 0.0
        assert geo["%1"]["height_pct"] == 0.0

    def test_capture_missing_pane(self):
        dims = {"%1": {"width": 80, "height": 24, "total_width": 160, "total_height": 48}}
        geo = capture_geometry(["%1", "%2"], dims)
        assert geo["%2"]["width_pct"] == 0.0

    def test_capture_full_width(self):
        dims = {"%1": {"width": 200, "height": 50, "total_width": 200, "total_height": 50}}
        geo = capture_geometry(["%1"], dims)
        assert geo["%1"]["width_pct"] == pytest.approx(100.0)
        assert geo["%1"]["height_pct"] == pytest.approx(100.0)

    def test_capture_zero_total(self):
        dims = {"%1": {"width": 10, "height": 10, "total_width": 0, "total_height": 0}}
        geo = capture_geometry(["%1"], dims)
        assert geo["%1"]["width_pct"] == 0.0

    def test_apply_basic(self):
        geo = {"%1": {"width_pct": 50.0, "height_pct": 50.0}}
        cmds = apply_geometry(geo, 200, 100)
        assert len(cmds) == 1
        assert cmds[0]["pane_id"] == "%1"
        assert cmds[0]["width"] == 100
        assert cmds[0]["height"] == 50

    def test_apply_empty(self):
        cmds = apply_geometry({}, 200, 100)
        assert cmds == []

    def test_apply_zero_terminal(self):
        geo = {"%1": {"width_pct": 50.0, "height_pct": 50.0}}
        cmds = apply_geometry(geo, 0, 0)
        assert cmds[0]["width"] == 0
        assert cmds[0]["height"] == 0

    def test_apply_rounds(self):
        geo = {"%1": {"width_pct": 33.3333, "height_pct": 66.6667}}
        cmds = apply_geometry(geo, 100, 100)
        assert cmds[0]["width"] == 33
        assert cmds[0]["height"] == 67


# ===========================================================================
# T053 — session save / restore
# ===========================================================================

class TestSession:
    def test_save_creates_files(self, tmp_path):
        mgr = _populated_manager()
        sd = str(tmp_path / "session")
        save_session(mgr, sd)
        assert os.path.isfile(os.path.join(sd, "stacks.json"))
        assert os.path.isfile(os.path.join(sd, "geometry.json"))

    def test_save_stacks_json_valid(self, tmp_path):
        mgr = _populated_manager()
        sd = str(tmp_path / "session")
        save_session(mgr, sd)
        with open(os.path.join(sd, "stacks.json")) as f:
            data = json.load(f)
        assert "%1" in data
        assert "%2" in data

    def test_restore_roundtrip(self, tmp_path):
        mgr = _populated_manager()
        sd = str(tmp_path / "session")
        save_session(mgr, sd)

        mgr2 = StackManager()
        deferred = restore_session(mgr2, sd)
        assert set(mgr2.all_stacks().keys()) == {"%1", "%2"}
        assert deferred.pending_count() > 0

    def test_restore_missing_dir(self, tmp_path):
        mgr = StackManager()
        sd = str(tmp_path / "nonexistent")
        deferred = restore_session(mgr, sd)
        assert deferred.pending_count() == 0
        assert mgr.all_stacks() == {}

    def test_restore_deferred_tabs_match(self, tmp_path):
        mgr = _populated_manager()
        sd = str(tmp_path / "session")
        save_session(mgr, sd)

        mgr2 = StackManager()
        deferred = restore_session(mgr2, sd)
        tabs_p1 = deferred.apply_pending("%1")
        assert len(tabs_p1) == 2
        tabs_p2 = deferred.apply_pending("%2")
        assert len(tabs_p2) == 1

    def test_load_geometry(self, tmp_path):
        mgr = _populated_manager()
        dims = {
            "%1": {"width": 80, "height": 24, "total_width": 160, "total_height": 48},
            "%2": {"width": 80, "height": 24, "total_width": 160, "total_height": 48},
        }
        sd = str(tmp_path / "session")
        save_session(mgr, sd, pane_dimensions=dims)
        geo = load_geometry(sd)
        assert "%1" in geo
        assert geo["%1"]["width_pct"] == pytest.approx(50.0)

    def test_load_geometry_missing(self, tmp_path):
        geo = load_geometry(str(tmp_path / "nope"))
        assert geo == {}

    def test_save_empty_manager(self, tmp_path):
        mgr = StackManager()
        sd = str(tmp_path / "session")
        save_session(mgr, sd)
        with open(os.path.join(sd, "stacks.json")) as f:
            assert json.load(f) == {}
