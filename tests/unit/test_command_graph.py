import importlib.util
import sys
import os
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

node_mod = _load_module("engine.graph.node", "core/engine/graph/node.py")
loader_mod = _load_module("engine.graph.loader", "core/engine/graph/loader.py")
resolver_mod = _load_module("engine.graph.resolver", "core/engine/graph/resolver.py")

CommandGraphNode = node_mod.CommandGraphNode
NodeType = node_mod.NodeType
ActionKind = node_mod.ActionKind
Scope = node_mod.Scope
load_nodes_from_yaml = loader_mod.load_nodes_from_yaml
load_nodes_from_directory = loader_mod.load_nodes_from_directory
merge_node = resolver_mod.merge_node
resolve_tree = resolver_mod.resolve_tree


# ─── Node model tests ───────────────────────────────────────────────


class TestNodeModel:
    def test_create_node_all_fields(self):
        child = CommandGraphNode(id="c1", label="Child", type=NodeType.ACTION)
        node = CommandGraphNode(
            id="n1",
            label="Test Node",
            type=NodeType.GROUP,
            scope=Scope.WORKSPACE,
            action_kind=ActionKind.SHELL,
            command="echo hi",
            children=[child],
            resolver="custom",
            timeout_ms=5000,
            cache_ttl_s=60,
            config_file="test.conf",
            tags=["a", "b"],
            icon="star",
            description="A test node",
            disabled=True,
            source_file="test.yaml",
        )
        assert node.id == "n1"
        assert node.label == "Test Node"
        assert node.type == NodeType.GROUP
        assert node.scope == Scope.WORKSPACE
        assert node.action_kind == ActionKind.SHELL
        assert node.command == "echo hi"
        assert len(node.children) == 1
        assert node.resolver == "custom"
        assert node.timeout_ms == 5000
        assert node.cache_ttl_s == 60
        assert node.config_file == "test.conf"
        assert node.tags == ["a", "b"]
        assert node.icon == "star"
        assert node.description == "A test node"
        assert node.disabled is True
        assert node.source_file == "test.yaml"

    def test_node_type_enum_values(self):
        assert NodeType.ACTION.value == "action"
        assert NodeType.GROUP.value == "group"
        assert NodeType.LIVE_SOURCE.value == "live_source"
        assert NodeType.SETTING.value == "setting"

    def test_action_kind_enum_values(self):
        assert ActionKind.SHELL.value == "shell"
        assert ActionKind.PYTHON.value == "python"
        assert ActionKind.INTERNAL.value == "internal"
        assert ActionKind.NAVIGATION.value == "navigation"

    def test_scope_enum_values(self):
        assert Scope.GLOBAL.value == "global"
        assert Scope.PROFILE.value == "profile"
        assert Scope.WORKSPACE.value == "workspace"

    def test_default_values(self):
        node = CommandGraphNode(id="d1", label="Defaults", type=NodeType.ACTION)
        assert node.scope == Scope.GLOBAL
        assert node.action_kind is None
        assert node.command is None
        assert node.children == []
        assert node.resolver is None
        assert node.timeout_ms == 3000
        assert node.cache_ttl_s == 30
        assert node.config_file is None
        assert node.tags == []
        assert node.icon is None
        assert node.description is None
        assert node.disabled is False
        assert node.source_file is None

    def test_children_list_is_mutable(self):
        node = CommandGraphNode(id="m1", label="Mutable", type=NodeType.GROUP)
        child = CommandGraphNode(id="mc1", label="Child", type=NodeType.ACTION)
        node.children.append(child)
        assert len(node.children) == 1
        assert node.children[0].id == "mc1"


# ─── YAML loader tests ──────────────────────────────────────────────


class TestYAMLLoader:
    def test_load_simple_action_node(self, tmp_path):
        yaml_file = tmp_path / "actions.yaml"
        yaml_file.write_text(
            '- id: actions.save\n'
            '  label: "Save Workspace"\n'
            '  type: action\n'
            '  action_kind: shell\n'
            '  command: "nexus-ctl workspace save"\n'
            '  tags: [workspace, save]\n'
        )
        nodes = load_nodes_from_yaml(str(yaml_file))
        assert len(nodes) == 1
        n = nodes[0]
        assert n.id == "actions.save"
        assert n.label == "Save Workspace"
        assert n.type == NodeType.ACTION
        assert n.action_kind == ActionKind.SHELL
        assert n.command == "nexus-ctl workspace save"
        assert set(n.tags) == {"workspace", "save"}

    def test_load_group_with_children(self, tmp_path):
        yaml_file = tmp_path / "groups.yaml"
        yaml_file.write_text(
            '- id: settings\n'
            '  label: "Settings"\n'
            '  type: group\n'
            '  children:\n'
            '    - id: settings.keymap\n'
            '      label: "Keybindings"\n'
            '      type: setting\n'
            '      config_file: "keymap.conf"\n'
        )
        nodes = load_nodes_from_yaml(str(yaml_file))
        assert len(nodes) == 1
        g = nodes[0]
        assert g.type == NodeType.GROUP
        assert len(g.children) == 1
        c = g.children[0]
        assert c.id == "settings.keymap"
        assert c.type == NodeType.SETTING
        assert c.config_file == "keymap.conf"

    def test_load_setting_node_with_config_file(self, tmp_path):
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text(
            '- id: s1\n'
            '  label: "Theme"\n'
            '  type: setting\n'
            '  config_file: "theme.conf"\n'
        )
        nodes = load_nodes_from_yaml(str(yaml_file))
        assert len(nodes) == 1
        assert nodes[0].config_file == "theme.conf"

    def test_load_nonexistent_file_returns_empty(self):
        nodes = load_nodes_from_yaml("/nonexistent/path/file.yaml")
        assert nodes == []

    def test_load_from_directory_multiple_files(self, tmp_path):
        (tmp_path / "a.yaml").write_text(
            '- id: a1\n  label: "A1"\n  type: action\n'
        )
        (tmp_path / "b.yaml").write_text(
            '- id: b1\n  label: "B1"\n  type: action\n'
        )
        nodes = load_nodes_from_directory(str(tmp_path), Scope.PROFILE)
        assert len(nodes) == 2
        ids = {n.id for n in nodes}
        assert ids == {"a1", "b1"}

    def test_scope_stamping(self, tmp_path):
        yaml_file = tmp_path / "scoped.yaml"
        yaml_file.write_text(
            '- id: x1\n'
            '  label: "X"\n'
            '  type: group\n'
            '  children:\n'
            '    - id: x1.c\n'
            '      label: "XC"\n'
            '      type: action\n'
        )
        nodes = load_nodes_from_directory(str(tmp_path), Scope.WORKSPACE)
        assert nodes[0].scope == Scope.WORKSPACE
        assert nodes[0].children[0].scope == Scope.WORKSPACE

    def test_invalid_yaml_returns_empty(self, tmp_path):
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text(":::not valid yaml[[[")
        nodes = load_nodes_from_yaml(str(yaml_file))
        assert nodes == []


# ─── Resolver tests ─────────────────────────────────────────────────


class TestResolver:
    def _node(self, id, label="L", type=NodeType.ACTION, **kwargs):
        return CommandGraphNode(id=id, label=label, type=type, **kwargs)

    def test_merge_node_overrides_scalar_fields(self):
        base = self._node("n", label="Old", command="old_cmd", icon="old_icon")
        override = self._node("n", label="New", command="new_cmd", icon="new_icon")
        merged = merge_node(base, override)
        assert merged.label == "New"
        assert merged.command == "new_cmd"
        assert merged.icon == "new_icon"

    def test_merge_node_unions_tags(self):
        base = self._node("n", tags=["a", "b"])
        override = self._node("n", tags=["b", "c"])
        merged = merge_node(base, override)
        assert set(merged.tags) == {"a", "b", "c"}

    def test_merge_node_merges_children_by_id(self):
        base = self._node(
            "g", type=NodeType.GROUP,
            children=[self._node("c1", label="Base C1"), self._node("c2", label="Base C2")]
        )
        override = self._node(
            "g", type=NodeType.GROUP,
            children=[self._node("c1", label="Override C1")]
        )
        merged = merge_node(base, override)
        assert len(merged.children) == 2
        c1 = next(c for c in merged.children if c.id == "c1")
        c2 = next(c for c in merged.children if c.id == "c2")
        assert c1.label == "Override C1"
        assert c2.label == "Base C2"

    def test_merge_node_disabled_flag(self):
        base = self._node("n", disabled=False)
        override = self._node("n", disabled=True)
        merged = merge_node(base, override)
        assert merged.disabled is True

    def test_resolve_tree_single_scope(self):
        nodes = [self._node("a", label="A"), self._node("b", label="B")]
        result = resolve_tree([nodes])
        assert len(result) == 2

    def test_resolve_tree_two_scopes_override_wins(self):
        global_nodes = [self._node("n", label="Global")]
        profile_nodes = [self._node("n", label="Profile")]
        result = resolve_tree([global_nodes, profile_nodes])
        assert len(result) == 1
        assert result[0].label == "Profile"

    def test_resolve_tree_three_scopes_workspace_wins(self):
        g = [self._node("n", label="Global")]
        p = [self._node("n", label="Profile")]
        w = [self._node("n", label="Workspace")]
        result = resolve_tree([g, p, w])
        assert len(result) == 1
        assert result[0].label == "Workspace"

    def test_resolve_tree_removes_disabled(self):
        g = [self._node("n", label="Keep"), self._node("rm", label="Remove")]
        w = [self._node("rm", disabled=True)]
        result = resolve_tree([g, w])
        assert len(result) == 1
        assert result[0].id == "n"

    def test_resolve_tree_preserves_non_overridden(self):
        g = [self._node("a", label="A"), self._node("b", label="B")]
        p = [self._node("a", label="A2")]
        result = resolve_tree([g, p])
        assert len(result) == 2
        a = next(n for n in result if n.id == "a")
        b = next(n for n in result if n.id == "b")
        assert a.label == "A2"
        assert b.label == "B"

    def test_resolve_tree_nested_group_merge(self):
        g = [self._node(
            "grp", type=NodeType.GROUP,
            children=[self._node("c1", label="GC1"), self._node("c2", label="GC2")]
        )]
        w = [self._node(
            "grp", type=NodeType.GROUP,
            children=[self._node("c1", label="WC1")]
        )]
        result = resolve_tree([g, w])
        assert len(result) == 1
        grp = result[0]
        assert len(grp.children) == 2
        c1 = next(c for c in grp.children if c.id == "c1")
        assert c1.label == "WC1"

    def test_resolve_tree_empty_chain(self):
        assert resolve_tree([]) == []

    def test_merge_node_override_action_kind(self):
        base = self._node("n", action_kind=ActionKind.SHELL)
        override = self._node("n", action_kind=ActionKind.PYTHON)
        merged = merge_node(base, override)
        assert merged.action_kind == ActionKind.PYTHON

    def test_merge_node_preserves_base_when_override_none(self):
        base = self._node("n", command="keep", icon="keep_icon")
        override = self._node("n")
        merged = merge_node(base, override)
        assert merged.command == "keep"
        assert merged.icon == "keep_icon"
