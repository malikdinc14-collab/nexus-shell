"""Tests for menu_handler and capability_launcher (T035 / T036)."""

import importlib.util
import sys
import os
from unittest.mock import MagicMock, patch
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core"))


def _load_module(name, rel_path):
    if name in sys.modules:
        return sys.modules[name]
    full = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load dependencies
_load_module("engine.graph.node", "core/engine/graph/node.py")
_load_module("engine.graph.loader", "core/engine/graph/loader.py")
_load_module("engine.graph.resolver", "core/engine/graph/resolver.py")

menu_mod = _load_module("engine.api.menu_handler", "core/engine/api/menu_handler.py")
cap_mod = _load_module("engine.api.capability_launcher", "core/engine/api/capability_launcher.py")

from engine.graph.node import CommandGraphNode, NodeType, ActionKind, Scope
from engine.capabilities.base import CapabilityType, AdapterManifest, Capability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_node(id, label="", ntype=NodeType.ACTION, children=None, **kw):
    return CommandGraphNode(
        id=id, label=label or id, type=ntype,
        children=children or [], **kw,
    )


def _make_group(id, label="", children=None, **kw):
    return _make_node(id, label, NodeType.GROUP, children=children or [], **kw)


class _FakeAdapter(Capability):
    def __init__(self, name, cap_type, priority=100, available=True):
        self._name = name
        self._cap_type = cap_type
        self._available = available
        self.manifest = AdapterManifest(
            name=name, capability_type=cap_type, priority=priority,
        )

    @property
    def capability_type(self):
        return self._cap_type

    def is_available(self):
        return self._available


class _FakeRegistry:
    """Minimal stand-in for CapabilityRegistry used in capability_launcher tests."""

    def __init__(self, adapters=None):
        self._adapters = adapters or {}  # CapabilityType -> list of _FakeAdapter

    def list_all_with_manifests(self, cap_type):
        return [(a, a.manifest) for a in self._adapters.get(cap_type, [])]

    def get_best(self, cap_type):
        avail = [a for a in self._adapters.get(cap_type, []) if a.is_available()]
        if not avail:
            return None
        avail.sort(key=lambda a: a.manifest.priority, reverse=True)
        return avail[0]

    def get_launch_command(self, role):
        return f"fake-{role}" if role else None


# ===========================================================================
# menu_handler tests
# ===========================================================================

class TestBuildMenuItemsFlat:
    def test_flat_nodes_count(self):
        nodes = [_make_node("a"), _make_node("b")]
        items = menu_mod.build_menu_items(nodes)
        assert len(items) == 2

    def test_flat_nodes_depth_zero(self):
        items = menu_mod.build_menu_items([_make_node("x")])
        assert items[0]["depth"] == 0

    def test_item_contains_type_field(self):
        items = menu_mod.build_menu_items([_make_node("x")])
        assert items[0]["type"] == "action"

    def test_has_children_false_for_leaf(self):
        items = menu_mod.build_menu_items([_make_node("x")])
        assert items[0]["has_children"] is False


class TestBuildMenuItemsNested:
    def test_nested_group_increases_depth(self):
        child = _make_node("c1", "Child")
        group = _make_group("g1", "Group", children=[child])
        items = menu_mod.build_menu_items([group])
        assert items[0]["depth"] == 0
        assert items[1]["depth"] == 1

    def test_has_children_true_for_group(self):
        group = _make_group("g1", "Group", children=[_make_node("c1")])
        items = menu_mod.build_menu_items([group])
        assert items[0]["has_children"] is True

    def test_deeply_nested(self):
        inner = _make_node("inner")
        mid = _make_group("mid", children=[inner])
        outer = _make_group("outer", children=[mid])
        items = menu_mod.build_menu_items([outer])
        assert items[2]["depth"] == 2


class TestBuildMenuItemsSpecialTypes:
    def test_live_source_includes_resolver(self):
        node = _make_node("ls1", ntype=NodeType.LIVE_SOURCE, resolver="test.resolver")
        items = menu_mod.build_menu_items([node])
        assert items[0]["resolver"] == "test.resolver"

    def test_setting_includes_config_file(self):
        node = _make_node("s1", ntype=NodeType.SETTING, config_file="foo.yaml")
        items = menu_mod.build_menu_items([node])
        assert items[0]["config_file"] == "foo.yaml"

    def test_action_node_no_resolver_field(self):
        items = menu_mod.build_menu_items([_make_node("a1")])
        assert "resolver" not in items[0]


class TestHandleOpen:
    def test_returns_items_from_system_root(self):
        result = menu_mod.handle_open()
        assert result["action"] == "show_menu"
        assert result["source"] == "system_root"
        assert isinstance(result["items"], list)
        assert len(result["items"]) > 0

    def test_returns_seven_top_level_groups(self):
        result = menu_mod.handle_open()
        top_level = [i for i in result["items"] if i["depth"] == 0]
        assert len(top_level) == 7

    def test_missing_file_returns_error(self):
        with patch.object(menu_mod.os.path, "isfile", return_value=False):
            result = menu_mod.handle_open()
        assert result["error"] == "no_menu_file"
        assert result["items"] == []


class TestHandleSelect:
    @pytest.fixture()
    def nodes(self):
        action = _make_node("act1", command="echo hello", action_kind=ActionKind.SHELL)
        setting = _make_node(
            "set1", ntype=NodeType.SETTING, config_file="keymap.conf",
        )
        group = _make_group("grp", children=[action, setting])
        return [group]

    def test_new_tab_mode(self, nodes):
        result = menu_mod.handle_select("act1", mode="new_tab", nodes=nodes)
        assert result["action"] == "exec"
        assert result["mode"] == "new_tab"
        assert result["command"] == "echo hello"

    def test_replace_mode(self, nodes):
        result = menu_mod.handle_select("act1", mode="replace", nodes=nodes)
        assert result["mode"] == "replace"

    def test_edit_mode_for_setting(self, nodes):
        result = menu_mod.handle_select("set1", mode="edit", nodes=nodes)
        assert result["action"] == "edit"
        assert result["config_file"] == "keymap.conf"

    def test_unknown_node_returns_error(self, nodes):
        result = menu_mod.handle_select("nonexistent", nodes=nodes)
        assert result["error"] == "node_not_found"
        assert result["node_id"] == "nonexistent"


# ===========================================================================
# capability_launcher tests
# ===========================================================================

class TestCapabilityHandleOpen:
    @pytest.fixture()
    def registry(self):
        adapters = {
            CapabilityType.EDITOR: [_FakeAdapter("nvim", CapabilityType.EDITOR, 200)],
            CapabilityType.EXPLORER: [_FakeAdapter("yazi", CapabilityType.EXPLORER, 150)],
        }
        return _FakeRegistry(adapters)

    def test_returns_show_launcher_action(self, registry):
        result = cap_mod.handle_open(registry=registry)
        assert result["action"] == "show_launcher"

    def test_includes_all_capability_types(self, registry):
        result = cap_mod.handle_open(registry=registry)
        type_names = {c["type"] for c in result["capabilities"]}
        for ct in CapabilityType:
            assert ct.name in type_names

    def test_includes_adapters_list(self, registry):
        result = cap_mod.handle_open(registry=registry)
        editor = next(c for c in result["capabilities"] if c["type"] == "EDITOR")
        assert len(editor["adapters"]) == 1
        assert editor["adapters"][0]["name"] == "nvim"

    def test_includes_default_adapter(self, registry):
        result = cap_mod.handle_open(registry=registry)
        editor = next(c for c in result["capabilities"] if c["type"] == "EDITOR")
        assert editor["default"] == "nvim"

    def test_labels_are_human_readable(self, registry):
        result = cap_mod.handle_open(registry=registry)
        label_map = {c["type"]: c["label"] for c in result["capabilities"]}
        assert label_map["EDITOR"] == "Editor"
        assert label_map["EXPLORER"] == "File Explorer"
        assert label_map["EXECUTOR"] == "Terminal"
        assert label_map["AGENT"] == "AI Agent"
        assert label_map["CHAT"] == "Chat"
        assert label_map["MENU"] == "Menu"
        assert label_map["MULTIPLEXER"] == "Multiplexer"

    def test_no_adapters_yields_empty_list(self, registry):
        result = cap_mod.handle_open(registry=registry)
        # RENDERER capability removed — verify it's absent
        renderer_types = [c["type"] for c in result["capabilities"]]
        assert "RENDERER" not in renderer_types


class TestCapabilityHandleSelect:
    @pytest.fixture()
    def registry(self):
        adapters = {
            CapabilityType.EDITOR: [
                _FakeAdapter("nvim", CapabilityType.EDITOR, 200),
                _FakeAdapter("vim", CapabilityType.EDITOR, 100),
            ],
        }
        return _FakeRegistry(adapters)

    def test_returns_launch_action(self, registry):
        result = cap_mod.handle_select("EDITOR", registry=registry)
        assert result["action"] == "launch"

    def test_selects_best_adapter_by_default(self, registry):
        result = cap_mod.handle_select("EDITOR", registry=registry)
        assert result["adapter"] == "nvim"

    def test_specific_adapter(self, registry):
        result = cap_mod.handle_select("EDITOR", adapter_name="vim", registry=registry)
        assert result["adapter"] == "vim"

    def test_unknown_capability_type(self, registry):
        result = cap_mod.handle_select("NONEXISTENT", registry=registry)
        assert "error" in result
        assert result["capability_type"] == "NONEXISTENT"

    def test_mode_defaults_to_new_tab(self, registry):
        result = cap_mod.handle_select("EDITOR", registry=registry)
        assert result["mode"] == "new_tab"

    def test_mode_replace(self, registry):
        result = cap_mod.handle_select("EDITOR", mode="replace", registry=registry)
        assert result["mode"] == "replace"

    def test_command_field_present(self, registry):
        result = cap_mod.handle_select("EDITOR", registry=registry)
        assert "command" in result
        assert result["command"] == "fake-editor"

    def test_capability_type_preserved(self, registry):
        result = cap_mod.handle_select("EDITOR", registry=registry)
        assert result["capability_type"] == "EDITOR"
