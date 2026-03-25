"""Comprehensive tests for StackManager and stack_handler."""

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_module(name, rel_path):
    """Load a module by file path, reusing cached version if present."""
    if name in sys.modules:
        return sys.modules[name]
    full_path = PROJECT_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, full_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load dependency modules into sys.modules so relative imports resolve
sys.path.insert(0, str(PROJECT_ROOT / "core"))

stack_mod = _load_module("engine.stacks.stack", "core/engine/stacks/stack.py")
Tab = stack_mod.Tab
TabStack = stack_mod.TabStack

reservoir_mod = _load_module("engine.stacks.reservoir", "core/engine/stacks/reservoir.py")
TabReservoir = reservoir_mod.TabReservoir

manager_mod = _load_module("engine.stacks.manager", "core/engine/stacks/manager.py")
StackManager = manager_mod.StackManager
LastTabWarning = manager_mod.LastTabWarning
NativelyManaged = manager_mod.NativelyManaged

runtime_mod = _load_module("engine.api.runtime", "core/engine/api/runtime.py")
handler_mod = _load_module("engine.api.stack_handler", "core/engine/api/stack_handler.py")
handle_push = handler_mod.handle_push
handle_pop = handler_mod.handle_pop
handle_rotate = handler_mod.handle_rotate
get_manager = runtime_mod.get_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mgr():
    """Fresh StackManager for each test."""
    return StackManager()


@pytest.fixture(autouse=True)
def reset_handler_singleton():
    """Reset the shared runtime singleton between tests."""
    runtime_mod.reset()
    yield
    runtime_mod.reset()


def _make_tab(**kwargs):
    defaults = {"capability_type": "terminal", "adapter_name": "zsh"}
    defaults.update(kwargs)
    return Tab(**defaults)


# ===========================================================================
# StackManager tests
# ===========================================================================


class TestStackManagerGetOrCreate:
    def test_returns_new_stack(self, mgr):
        stack = mgr.get_or_create("%1")
        assert isinstance(stack, TabStack)
        assert stack.pane_id == "%1"

    def test_returns_existing_stack(self, mgr):
        s1 = mgr.get_or_create("%1")
        s2 = mgr.get_or_create("%1")
        assert s1 is s2

    def test_different_panes_get_different_stacks(self, mgr):
        s1 = mgr.get_or_create("%1")
        s2 = mgr.get_or_create("%2")
        assert s1 is not s2


class TestStackManagerPush:
    def test_push_adds_tab_to_correct_stack(self, mgr):
        tab = _make_tab()
        mgr.push("%1", tab)
        stack = mgr.get_stack("%1")
        assert len(stack.tabs) == 1
        assert stack.tabs[0] is tab

    def test_push_creates_stack_if_needed(self, mgr):
        tab = _make_tab()
        mgr.push("%5", tab)
        assert mgr.get_stack("%5") is not None

    def test_push_records_event(self, mgr):
        mgr.push("%1", _make_tab())
        assert "tab.pushed" in mgr.events

    def test_push_native_multiplicity_returns_sentinel(self, mgr):
        native_tab = _make_tab(native_multiplicity=True)
        mgr.get_or_create("%1").push(native_tab)
        result = mgr.push("%1", _make_tab())
        assert isinstance(result, NativelyManaged)

    def test_push_native_multiplicity_does_not_modify_stack(self, mgr):
        native_tab = _make_tab(native_multiplicity=True)
        mgr.get_or_create("%1").push(native_tab)
        mgr.push("%1", _make_tab())
        assert len(mgr.get_stack("%1").tabs) == 1


class TestStackManagerPop:
    def test_pop_returns_tab(self, mgr):
        tab1 = _make_tab()
        tab2 = _make_tab()
        mgr.push("%1", tab1)
        mgr.push("%1", tab2)
        popped = mgr.pop("%1")
        assert popped is tab2

    def test_pop_last_tab_returns_warning(self, mgr):
        mgr.push("%1", _make_tab())
        result = mgr.pop("%1")
        assert isinstance(result, LastTabWarning)

    def test_pop_empty_stack_returns_none(self, mgr):
        mgr.get_or_create("%1")
        result = mgr.pop("%1")
        assert result is None

    def test_pop_unknown_pane_returns_none(self, mgr):
        result = mgr.pop("%99")
        assert result is None

    def test_pop_records_event(self, mgr):
        mgr.push("%1", _make_tab())
        mgr.push("%1", _make_tab())
        mgr.events.clear()
        mgr.pop("%1")
        assert "tab.popped" in mgr.events

    def test_pop_native_multiplicity_returns_sentinel(self, mgr):
        native_tab = _make_tab(native_multiplicity=True)
        mgr.get_or_create("%1").push(native_tab)
        result = mgr.pop("%1")
        assert isinstance(result, NativelyManaged)


class TestStackManagerRotate:
    def test_rotate_changes_active_tab(self, mgr):
        tab1 = _make_tab()
        tab2 = _make_tab()
        mgr.push("%1", tab1)
        mgr.push("%1", tab2)
        result = mgr.rotate("%1", -1)
        assert result is tab1

    def test_rotate_wraps_around(self, mgr):
        tab1 = _make_tab()
        tab2 = _make_tab()
        mgr.push("%1", tab1)
        mgr.push("%1", tab2)
        result = mgr.rotate("%1", 1)
        assert result is tab1

    def test_rotate_single_tab_returns_none(self, mgr):
        mgr.push("%1", _make_tab())
        result = mgr.rotate("%1", 1)
        assert result is None

    def test_rotate_unknown_pane_returns_none(self, mgr):
        result = mgr.rotate("%99", 1)
        assert result is None

    def test_rotate_records_event(self, mgr):
        mgr.push("%1", _make_tab())
        mgr.push("%1", _make_tab())
        mgr.events.clear()
        mgr.rotate("%1", 1)
        assert "tab.rotated" in mgr.events

    def test_rotate_native_multiplicity_returns_sentinel(self, mgr):
        native_tab = _make_tab(native_multiplicity=True)
        mgr.get_or_create("%1").push(native_tab)
        result = mgr.rotate("%1", 1)
        assert isinstance(result, NativelyManaged)


class TestStackManagerMisc:
    def test_remove_stack(self, mgr):
        mgr.push("%1", _make_tab())
        mgr.remove_stack("%1")
        assert mgr.get_stack("%1") is None

    def test_remove_stack_nonexistent_no_error(self, mgr):
        mgr.remove_stack("%99")  # should not raise

    def test_all_stacks(self, mgr):
        mgr.get_or_create("%1")
        mgr.get_or_create("%2")
        stacks = mgr.all_stacks()
        assert set(stacks.keys()) == {"%1", "%2"}

    def test_get_stack_returns_none_for_unknown(self, mgr):
        assert mgr.get_stack("%99") is None

    def test_reservoir_attribute(self, mgr):
        assert isinstance(mgr.reservoir, TabReservoir)

    def test_events_list_starts_empty(self, mgr):
        assert mgr.events == []


# ===========================================================================
# stack_handler tests
# ===========================================================================


class TestHandlePush:
    def test_creates_and_pushes_tab(self):
        tab = handle_push("%1", capability_type="editor", adapter_name="neovim")
        assert isinstance(tab, Tab)
        assert tab.capability_type == "editor"
        assert tab.adapter_name == "neovim"

    def test_tab_appears_in_manager(self):
        handle_push("%1")
        mgr = get_manager()
        stack = mgr.get_stack("%1")
        assert len(stack.tabs) == 1

    def test_push_with_defaults(self):
        tab = handle_push("%1")
        assert tab.capability_type == "terminal"
        assert tab.adapter_name == "zsh"

    def test_push_native_returns_sentinel(self):
        mgr = get_manager()
        native_tab = _make_tab(native_multiplicity=True)
        mgr.get_or_create("%1").push(native_tab)
        result = handle_push("%1")
        assert isinstance(result, NativelyManaged)


class TestHandlePop:
    def test_returns_tab(self):
        handle_push("%1")
        handle_push("%1")
        result = handle_pop("%1")
        assert isinstance(result, Tab)

    def test_last_tab_returns_warning_dict(self):
        handle_push("%1")
        result = handle_pop("%1")
        assert result == {"warning": "last_tab", "pane_id": "%1"}

    def test_native_returns_delegated_dict(self):
        mgr = get_manager()
        native_tab = _make_tab(native_multiplicity=True)
        mgr.get_or_create("%1").push(native_tab)
        result = handle_pop("%1")
        assert result == {"delegated": True}

    def test_empty_returns_none(self):
        result = handle_pop("%99")
        assert result is None


class TestHandleRotate:
    def test_returns_active_tab(self):
        handle_push("%1")
        handle_push("%1")
        result = handle_rotate("%1", -1)
        assert isinstance(result, Tab)

    def test_single_tab_returns_none(self):
        handle_push("%1")
        result = handle_rotate("%1", 1)
        assert result is None


class TestGetManager:
    def test_returns_singleton(self):
        m1 = get_manager()
        m2 = get_manager()
        assert m1 is m2

    def test_creates_new_if_none(self):
        runtime_mod.reset()
        mgr = get_manager()
        assert isinstance(mgr, StackManager)
