"""Tests for T020/T021/T022: modeless keymap, pane_handler, tab_manager.

Covers nexus.conf keybinding verification, pane_handler operations,
and tab_manager list/jump operations.
"""

import importlib.util
import os
import re
import sys
import pytest

# ---------------------------------------------------------------------------
# Import helpers — load modules from project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONF_PATH = os.path.join(PROJECT_ROOT, "config", "tmux", "nexus.conf")


def _load_module(name: str, rel_path: str):
    """Load a Python module by relative path, reusing cached version if present."""
    if name in sys.modules:
        return sys.modules[name]
    full = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load dependency chain into sys.modules so `from engine.X` resolves
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))

_stack_mod = _load_module("engine.stacks.stack", "core/engine/stacks/stack.py")
_reservoir_mod = _load_module("engine.stacks.reservoir", "core/engine/stacks/reservoir.py")
_manager_mod = _load_module("engine.stacks.manager", "core/engine/stacks/manager.py")
_runtime_mod = _load_module("engine.api.runtime", "core/engine/api/runtime.py")
_pane_mod = _load_module("engine.api.pane_handler", "core/engine/api/pane_handler.py")
_tab_mod = _load_module("engine.api.tab_manager", "core/engine/api/tab_manager.py")

Tab = _stack_mod.Tab
StackManager = _manager_mod.StackManager


# ---------------------------------------------------------------------------
# Fixture: read nexus.conf once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def conf_lines():
    with open(CONF_PATH) as f:
        return f.readlines()


def _find_binding(lines, key):
    """Find the bind-key line for the given key (e.g. 'M-m')."""
    pattern = re.compile(rf'^\s*bind-key\s+-n\s+{re.escape(key)}\s+(.+)$')
    for line in lines:
        m = pattern.match(line)
        if m:
            return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# Fixture: set up StackManager with tabs for pane/tab handler tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=False)
def pane_handler_with_stack():
    """Set up pane_handler with a fresh StackManager containing test tabs."""
    mgr = StackManager()
    _runtime_mod.set_manager(mgr)

    # Create a stack with 3 tabs for pane %5
    stack = mgr.get_or_create("%5")
    for i, (ctype, adapter) in enumerate([
        ("editor", "neovim"),
        ("terminal", "zsh"),
        ("chat", "opencode"),
    ]):
        tab = Tab(capability_type=ctype, adapter_name=adapter, role=f"role{i}")
        stack.push(tab)

    yield _pane_mod, mgr

    # Cleanup
    _runtime_mod.reset()


@pytest.fixture(autouse=False)
def tab_manager_with_stack():
    """Set up tab_manager with a fresh StackManager containing test tabs."""
    mgr = StackManager()
    _runtime_mod.set_manager(mgr)

    # Create a stack with 3 tabs for pane %10
    stack = mgr.get_or_create("%10")
    for i, (ctype, adapter) in enumerate([
        ("editor", "neovim"),
        ("terminal", "zsh"),
        ("chat", "opencode"),
    ]):
        tab = Tab(capability_type=ctype, adapter_name=adapter, role=f"role{i}")
        stack.push(tab)

    yield _tab_mod, mgr

    # Cleanup
    _runtime_mod.reset()


# ===================================================================
# nexus.conf keybinding verification (11 tests)
# ===================================================================

class TestNexusConfBindings:

    def test_alt_m_routes_to_menu_open(self, conf_lines):
        binding = _find_binding(conf_lines, "M-m")
        assert binding is not None
        assert "menu" in binding

    def test_alt_o_routes_to_capability_open(self, conf_lines):
        binding = _find_binding(conf_lines, "M-o")
        assert binding is not None
        assert "capability" in binding

    def test_alt_t_routes_to_tabs_list(self, conf_lines):
        binding = _find_binding(conf_lines, "M-t")
        assert binding is not None
        assert "tab" in binding

    def test_alt_n_routes_to_stack_push(self, conf_lines):
        binding = _find_binding(conf_lines, "M-n")
        assert binding is not None
        assert "stack" in binding and "push" in binding

    def test_alt_w_routes_to_stack_pop(self, conf_lines):
        binding = _find_binding(conf_lines, "M-w")
        assert binding is not None
        assert "stack" in binding and "pop" in binding

    def test_alt_bracket_left_routes_to_stack_rotate_back(self, conf_lines):
        binding = _find_binding(conf_lines, "M-[")
        assert binding is not None
        assert "stack" in binding and "rotate" in binding
        assert "-1" in binding

    def test_alt_bracket_right_routes_to_stack_rotate_forward(self, conf_lines):
        binding = _find_binding(conf_lines, "M-]")
        assert binding is not None
        assert "stack" in binding and "rotate" in binding
        assert "1" in binding

    def test_alt_q_routes_to_pane_kill(self, conf_lines):
        binding = _find_binding(conf_lines, "M-q")
        assert binding is not None
        assert "pane" in binding and "kill" in binding

    def test_alt_v_routes_to_pane_split_v(self, conf_lines):
        binding = _find_binding(conf_lines, "M-v")
        assert binding is not None
        assert "pane" in binding and "split" in binding and "v" in binding

    def test_alt_s_routes_to_pane_split_h(self, conf_lines):
        binding = _find_binding(conf_lines, "M-s")
        assert binding is not None
        assert "pane" in binding and "split" in binding and "h" in binding

    def test_alt_hjkl_route_to_select_pane(self, conf_lines):
        for key, direction in [("M-h", "-L"), ("M-j", "-D"), ("M-k", "-U"), ("M-l", "-R")]:
            binding = _find_binding(conf_lines, key)
            assert binding is not None, f"{key} binding missing"
            assert f"select-pane {direction}" in binding, f"{key} should select-pane {direction}"

    def test_old_mosaic_engine_binding_removed(self, conf_lines):
        full_text = "".join(conf_lines)
        assert "mosaic_engine" not in full_text

    def test_old_swap_sh_binding_removed(self, conf_lines):
        full_text = "".join(conf_lines)
        assert "swap.sh" not in full_text


# ===================================================================
# pane_handler tests (6 tests)
# ===================================================================

class TestPaneHandler:

    def test_handle_kill_returns_correct_structure(self, pane_handler_with_stack):
        mod, mgr = pane_handler_with_stack
        result = mod.handle_kill("%5")
        assert result["action"] == "kill_pane"
        assert result["pane_id"] == "%5"
        assert "tabs_shelved" in result

    def test_handle_kill_shelves_tabs(self, pane_handler_with_stack):
        mod, mgr = pane_handler_with_stack
        result = mod.handle_kill("%5")
        assert result["tabs_shelved"] == 3
        # Tabs should be in the reservoir
        assert len(mgr.reservoir.tabs) == 3

    def test_handle_kill_no_stack_returns_zero(self, pane_handler_with_stack):
        mod, mgr = pane_handler_with_stack
        result = mod.handle_kill("%999")
        assert result["action"] == "kill_pane"
        assert result["pane_id"] == "%999"
        assert result["tabs_shelved"] == 0

    def test_handle_split_returns_correct_action(self, pane_handler_with_stack):
        mod, _ = pane_handler_with_stack
        result = mod.handle_split("%5", "v")
        assert result["action"] == "split"
        assert result["new_pane"] == "pending"
        assert result["parent_pane"] == "%5"

    def test_handle_split_direction_v(self, pane_handler_with_stack):
        mod, _ = pane_handler_with_stack
        result = mod.handle_split("%5", "v")
        assert result["direction"] == "v"

    def test_handle_split_direction_h(self, pane_handler_with_stack):
        mod, _ = pane_handler_with_stack
        result = mod.handle_split("%5", "h")
        assert result["direction"] == "h"


# ===================================================================
# tab_manager tests (5 tests)
# ===================================================================

class TestTabManager:

    def test_handle_list_returns_tab_list(self, tab_manager_with_stack):
        mod, mgr = tab_manager_with_stack
        result = mod.handle_list("%10")
        assert result["pane_id"] == "%10"
        assert len(result["tabs"]) == 3
        # Check tab structure
        tab = result["tabs"][0]
        assert "id" in tab
        assert "type" in tab
        assert "adapter" in tab
        assert "role" in tab
        assert "active" in tab

    def test_handle_list_with_empty_stack(self, tab_manager_with_stack):
        mod, mgr = tab_manager_with_stack
        # Create an empty stack
        mgr.get_or_create("%empty")
        result = mod.handle_list("%empty")
        assert result["pane_id"] == "%empty"
        assert result["tabs"] == []
        assert result["active_index"] == 0

    def test_handle_list_no_stack_returns_empty(self, tab_manager_with_stack):
        mod, _ = tab_manager_with_stack
        result = mod.handle_list("%nonexistent")
        assert result["pane_id"] == "%nonexistent"
        assert result["tabs"] == []
        assert result["active_index"] == 0

    def test_handle_jump_valid_index(self, tab_manager_with_stack):
        mod, mgr = tab_manager_with_stack
        result = mod.handle_jump("%10", 0)
        assert result["pane_id"] == "%10"
        assert result["jumped_to"] == 0
        assert "tab" in result
        assert result["tab"]["type"] == "editor"
        # Verify the tab is now active
        stack = mgr.get_stack("%10")
        assert stack.active_index == 0
        assert stack.tabs[0].is_active is True

    def test_handle_jump_out_of_range(self, tab_manager_with_stack):
        mod, _ = tab_manager_with_stack
        result = mod.handle_jump("%10", 99)
        assert result["error"] == "index_out_of_range"
        assert result["max"] == 2
