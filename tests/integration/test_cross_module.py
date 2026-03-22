"""Cross-module integration tests for nexus-shell Phase 10 verification.

Verifies correctness properties P-01 through P-14 via cross-module
interactions WITHOUT requiring a live tmux session.
"""

import importlib.util
import json
import os
import sys
import tempfile

import pytest
import yaml

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

# -- Stack / Momentum modules ------------------------------------------------
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
    "engine.momentum.geometry", "core/engine/momentum/geometry.py"
)
_session_mod = _load_module(
    "engine.momentum.session", "core/engine/momentum/session.py"
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

# -- Command Graph / Menu modules --------------------------------------------
_node_mod = _load_module("engine.graph.node", "core/engine/graph/node.py")
_loader_mod = _load_module("engine.graph.loader", "core/engine/graph/loader.py")
_resolver_mod = _load_module("engine.graph.resolver", "core/engine/graph/resolver.py")
_menu_mod = _load_module("engine.api.menu_handler", "core/engine/api/menu_handler.py")

CommandGraphNode = _node_mod.CommandGraphNode
NodeType = _node_mod.NodeType
ActionKind = _node_mod.ActionKind
Scope = _node_mod.Scope
load_nodes_from_yaml = _loader_mod.load_nodes_from_yaml
resolve_tree = _resolver_mod.resolve_tree
build_menu_items = _menu_mod.build_menu_items

# -- Pack / Profile modules --------------------------------------------------
_pack_mod = _load_module("engine.packs.pack", "core/engine/packs/pack.py")
_detector_mod = _load_module("engine.packs.detector", "core/engine/packs/detector.py")
_pack_mgr_mod = _load_module("engine.packs.manager", "core/engine/packs/manager.py")
_profile_mod = _load_module("engine.profiles.manager", "core/engine/profiles/manager.py")

Pack = _pack_mod.Pack
load_pack_from_yaml = _pack_mod.load_pack_from_yaml
detect_markers = _detector_mod.detect_markers
suggest_packs = _detector_mod.suggest_packs
PackManager = _pack_mgr_mod.PackManager
Profile = _profile_mod.Profile
ProfileManager = _profile_mod.ProfileManager

# -- Config cascade / Theme / Keymap -----------------------------------------
from engine.config.cascade import CascadeResolver
from engine.config.theme_engine import Theme, load_theme, generate_tmux_commands
_keymap_mod = _load_module(
    "engine.config.keymap_loader", "core/engine/config/keymap_loader.py"
)
parse_keymap = _keymap_mod.parse_keymap
generate_bindings = _keymap_mod.generate_bindings

# -- Event Bus / Connectors --------------------------------------------------
_typed_mod = _load_module("engine.bus.typed_events", "core/engine/bus/typed_events.py")
_bus_mod = _load_module("engine.bus.enhanced_bus", "core/engine/bus/enhanced_bus.py")
_conn_mod = _load_module("connectors_engine", "core/engine/connectors/engine.py")

EventType = _typed_mod.EventType
TypedEvent = _typed_mod.TypedEvent
create_event = _typed_mod.create_event
EnhancedBus = _bus_mod.EnhancedBus
ConnectorDef = _conn_mod.ConnectorDef
ConnectorEngine = _conn_mod.ConnectorEngine
load_connectors_from_yaml = _conn_mod.load_connectors_from_yaml

# -- Paths -------------------------------------------------------------------
EXAMPLES_PACKS = os.path.join(PROJECT_ROOT, "core", "engine", "packs", "examples")
EXAMPLES_PROFILES = os.path.join(PROJECT_ROOT, "core", "engine", "profiles", "examples")
SYSTEM_ROOT_YAML = os.path.join(PROJECT_ROOT, "core", "ui", "menus", "system_root.yaml")
CATPPUCCIN_THEME = os.path.join(
    PROJECT_ROOT, "core", "engine", "config", "themes", "catppuccin.yaml"
)


# ============================================================================
# Helpers
# ============================================================================

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


def _write_yaml(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


# ============================================================================
# Stack + Momentum integration  (P-01, P-14)
# ============================================================================


class TestStackMomentumIntegration:
    """Cross-module tests: StackManager <-> stack_persistence <-> session."""

    def test_push_serialize_deserialize_roundtrip(self):
        """P-01/P-14: push tabs, serialize, deserialize into new manager."""
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        mgr2 = StackManager()
        deserialize_stacks(data, mgr2)
        assert set(mgr2.all_stacks().keys()) == {"%1", "%2"}
        assert len(mgr2.get_stack("%1").tabs) == 2
        assert len(mgr2.get_stack("%2").tabs) == 1

    def test_roundtrip_preserves_tab_fields(self):
        """P-14: all tab fields survive serialize/deserialize."""
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        mgr2 = StackManager()
        deserialize_stacks(data, mgr2)
        tab = mgr2.get_stack("%2").tabs[0]
        assert tab.capability_type == "chat"
        assert tab.adapter_name == "opencode"
        assert tab.command == "opencode"
        assert tab.env == {"TERM": "xterm"}
        assert tab.role == "shell"

    def test_roundtrip_via_json(self):
        """P-14: serialize -> JSON -> deserialize is lossless."""
        mgr = _populated_manager()
        data = serialize_stacks(mgr)
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        mgr2 = StackManager()
        deserialize_stacks(loaded, mgr2)
        assert len(mgr2.get_stack("%1").tabs) == 2

    def test_session_save_restore_roundtrip(self, tmp_path):
        """P-14: full session save/restore preserves stacks."""
        mgr = _populated_manager()
        session_dir = str(tmp_path / "session")
        dims = {
            "%1": {"width": 80, "height": 24, "total_width": 160, "total_height": 48},
            "%2": {"width": 80, "height": 24, "total_width": 160, "total_height": 48},
        }
        save_session(mgr, session_dir, pane_dimensions=dims)
        mgr2 = StackManager()
        deferred = restore_session(mgr2, session_dir)
        assert set(mgr2.all_stacks().keys()) == {"%1", "%2"}
        assert deferred.pending_count() == 3  # 2 tabs in %1 + 1 in %2

    def test_deferred_restore_apply_pending(self, tmp_path):
        """P-14: deferred restore queues tabs, apply clears them."""
        mgr = _populated_manager()
        session_dir = str(tmp_path / "session")
        save_session(mgr, session_dir)
        mgr2 = StackManager()
        deferred = restore_session(mgr2, session_dir)
        tabs_1 = deferred.apply_pending("%1")
        assert len(tabs_1) == 2
        assert deferred.apply_pending("%1") == []  # cleared after apply

    def test_geometry_capture_apply_roundtrip(self):
        """P-14: geometry capture -> apply produces consistent resize commands."""
        pane_ids = ["%1", "%2"]
        dims = {
            "%1": {"width": 80, "height": 24, "total_width": 160, "total_height": 48},
            "%2": {"width": 80, "height": 24, "total_width": 160, "total_height": 48},
        }
        geo = capture_geometry(pane_ids, dims)
        assert "%1" in geo
        assert abs(geo["%1"]["width_pct"] - 50.0) < 0.01
        commands = apply_geometry(geo, 200, 60)
        assert len(commands) == 2
        assert commands[0]["width"] == 100  # 50% of 200

    def test_session_geometry_file_written(self, tmp_path):
        """P-14: save_session writes geometry.json alongside stacks.json."""
        mgr = _populated_manager()
        session_dir = str(tmp_path / "session")
        save_session(mgr, session_dir)
        assert os.path.isfile(os.path.join(session_dir, "stacks.json"))
        assert os.path.isfile(os.path.join(session_dir, "geometry.json"))

    def test_load_geometry_after_save(self, tmp_path):
        """P-14: load_geometry returns saved geometry data."""
        mgr = _populated_manager()
        session_dir = str(tmp_path / "session")
        dims = {
            "%1": {"width": 80, "height": 24, "total_width": 160, "total_height": 48},
        }
        save_session(mgr, session_dir, pane_dimensions=dims)
        geo = load_geometry(session_dir)
        assert "%1" in geo


# ============================================================================
# Command Graph + Menu + Packs integration  (P-03, P-05, P-06, P-08)
# ============================================================================


class TestGraphMenuPacksIntegration:
    """Cross-module tests: graph loader -> resolver -> menu builder -> packs."""

    def test_load_system_root_yaml(self):
        """Load system_root.yaml through graph loader, verify structure."""
        if not os.path.isfile(SYSTEM_ROOT_YAML):
            pytest.skip("system_root.yaml not found")
        nodes = load_nodes_from_yaml(SYSTEM_ROOT_YAML)
        assert len(nodes) > 0
        assert all(isinstance(n, CommandGraphNode) for n in nodes)

    def test_build_menu_from_loaded_nodes(self):
        """Build menu items from loaded graph nodes."""
        if not os.path.isfile(SYSTEM_ROOT_YAML):
            pytest.skip("system_root.yaml not found")
        nodes = load_nodes_from_yaml(SYSTEM_ROOT_YAML)
        items = build_menu_items(nodes)
        assert len(items) > 0
        assert all("id" in item and "label" in item for item in items)

    def test_resolve_tree_workspace_overrides(self):
        """P-03: workspace scope overrides profile overrides global."""
        global_nodes = [
            CommandGraphNode(id="n1", label="Global", type=NodeType.ACTION, scope=Scope.GLOBAL),
        ]
        profile_nodes = [
            CommandGraphNode(id="n1", label="Profile", type=NodeType.ACTION, scope=Scope.PROFILE),
        ]
        workspace_nodes = [
            CommandGraphNode(id="n1", label="Workspace", type=NodeType.ACTION, scope=Scope.WORKSPACE),
        ]
        result = resolve_tree([global_nodes, profile_nodes, workspace_nodes])
        assert len(result) == 1
        assert result[0].label == "Workspace"

    def test_resolve_tree_disabled_node_removed(self):
        """P-03: disabled nodes are pruned from resolved tree."""
        global_nodes = [
            CommandGraphNode(id="n1", label="Keep", type=NodeType.ACTION),
            CommandGraphNode(id="n2", label="Remove", type=NodeType.ACTION),
        ]
        override = [
            CommandGraphNode(id="n2", label="Remove", type=NodeType.ACTION, disabled=True),
        ]
        result = resolve_tree([global_nodes, override])
        ids = [n.id for n in result]
        assert "n1" in ids
        assert "n2" not in ids

    def test_load_example_packs_have_markers(self):
        """P-05: example packs define marker files for detection."""
        if not os.path.isdir(EXAMPLES_PACKS):
            pytest.skip("example packs dir not found")
        mgr = PackManager([EXAMPLES_PACKS])
        assert len(mgr.available_packs) > 0
        for pack in mgr.available_packs:
            assert isinstance(pack.markers, list)

    def test_suggest_packs_for_matching_markers(self, tmp_path):
        """P-05: suggest_packs returns matches but never auto-enables."""
        pack_dir = tmp_path / "packs"
        pack_dir.mkdir()
        _write_yaml(str(pack_dir / "python.yaml"), {
            "name": "python",
            "markers": ["pyproject.toml", "setup.py"],
        })
        proj = tmp_path / "project"
        proj.mkdir()
        (proj / "pyproject.toml").touch()
        mgr = PackManager([str(pack_dir)])
        suggestions = mgr.suggest(str(proj))
        assert len(suggestions) == 1
        assert suggestions[0].name == "python"
        # P-05: never auto-enabled
        assert suggestions[0].enabled is False

    def test_pack_enable_disable_no_profile_change(self, tmp_path):
        """P-06/P-08: pack enable/disable does not affect profile state."""
        pack_dir = tmp_path / "packs"
        pack_dir.mkdir()
        _write_yaml(str(pack_dir / "rust.yaml"), {"name": "rust", "markers": ["Cargo.toml"]})
        prof_dir = tmp_path / "profiles"
        prof_dir.mkdir()
        _write_yaml(str(prof_dir / "work.yaml"), {"name": "work", "description": "Work"})

        pack_mgr = PackManager([str(pack_dir)])
        prof_mgr = ProfileManager(str(prof_dir))
        prof_mgr.switch("work")
        assert prof_mgr.active_profile.name == "work"

        pack_mgr.enable("rust")
        assert pack_mgr.get("rust").enabled is True
        assert prof_mgr.active_profile.name == "work"  # unchanged

        pack_mgr.disable("rust")
        assert pack_mgr.get("rust").enabled is False
        assert prof_mgr.active_profile.name == "work"  # still unchanged

    def test_pack_enable_is_idempotent(self, tmp_path):
        """P-07: enabling an already-enabled pack is idempotent."""
        pack_dir = tmp_path / "packs"
        pack_dir.mkdir()
        _write_yaml(str(pack_dir / "docker.yaml"), {"name": "docker", "markers": ["Dockerfile"]})
        mgr = PackManager([str(pack_dir)])
        mgr.enable("docker")
        mgr.enable("docker")
        assert mgr.get("docker").enabled is True
        mgr.disable("docker")
        mgr.disable("docker")
        assert mgr.get("docker").enabled is False


# ============================================================================
# Config cascade + Theme + Keymap integration  (P-02, P-04, P-12)
# ============================================================================


class TestConfigThemeKeymapIntegration:
    """Cross-module tests: cascade resolver, theme engine, keymap loader."""

    def test_cascade_workspace_overrides_profile_overrides_global(self, tmp_path):
        """P-02: workspace > profile > global resolution."""
        global_dir = tmp_path / "global"
        ws_dir = tmp_path / "ws" / ".nexus"
        profile_dir = global_dir / "profiles" / "dev"

        _write_yaml(str(global_dir / "adapters.yaml"), {"editor": "nano"})
        _write_yaml(str(profile_dir / "adapters.yaml"), {"editor": "vim"})
        _write_yaml(str(ws_dir / "adapters.yaml"), {"editor": "helix"})

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=ws_dir,
            profile="dev",
        )
        assert resolver.get("adapters.yaml", "editor") == "helix"

    def test_cascade_profile_overrides_global(self, tmp_path):
        """P-02: profile overrides global when no workspace value."""
        global_dir = tmp_path / "global"
        profile_dir = global_dir / "profiles" / "dev"

        _write_yaml(str(global_dir / "adapters.yaml"), {"editor": "nano"})
        _write_yaml(str(profile_dir / "adapters.yaml"), {"editor": "vim"})

        resolver = CascadeResolver(
            global_dir=global_dir,
            workspace_dir=tmp_path / "no_ws",
            profile="dev",
        )
        assert resolver.get("adapters.yaml", "editor") == "vim"

    def test_theme_load_and_generate_tmux_commands(self):
        """P-12: load theme YAML and generate valid tmux commands."""
        if not os.path.isfile(CATPPUCCIN_THEME):
            pytest.skip("catppuccin theme not found")
        theme = load_theme(CATPPUCCIN_THEME)
        assert theme is not None
        assert theme.name == "catppuccin"
        commands = generate_tmux_commands(theme)
        assert len(commands) == 5
        for cmd in commands:
            assert cmd.startswith("set -g ") or cmd.startswith("set -g ")

    def test_theme_commands_are_valid_set_option_strings(self):
        """P-12: generated commands are valid tmux set-option format."""
        theme = Theme(name="test", colors={
            "bg": "#000", "fg": "#fff", "accent": "#0ff",
            "border": "#333", "active_border": "#0ff",
            "status_bg": "#000", "status_fg": "#fff",
            "message_bg": "#000", "message_fg": "#0ff",
        })
        commands = generate_tmux_commands(theme)
        for cmd in commands:
            assert "set -g" in cmd
            # Should contain a quoted value
            assert '"' in cmd

    def test_keymap_parse_and_generate_bindings(self, tmp_path):
        """P-04: parse keymap, generate valid tmux bind-key strings."""
        km = tmp_path / "keymap.conf"
        km.write_text(
            "Alt+m = nexus-ctl menu open\n"
            "Alt+p = nexus-ctl pack suggest\n"
            "# comment line\n"
            "\n"
            "Alt+t = nexus-ctl theme cycle\n"
        )
        entries = parse_keymap(str(km))
        assert len(entries) == 3
        assert entries[0] == ("M-m", "nexus-ctl menu open")
        bindings = generate_bindings(entries)
        assert len(bindings) == 3
        for b in bindings:
            assert b.startswith("bind-key -n M-")
            assert "run-shell" in b

    def test_keymap_alt_keys_non_conflicting(self, tmp_path):
        """P-04: all Alt+key bindings are unique (no conflicts)."""
        km = tmp_path / "keymap.conf"
        km.write_text(
            "Alt+m = cmd1\nAlt+p = cmd2\nAlt+t = cmd3\nAlt+r = cmd4\n"
        )
        entries = parse_keymap(str(km))
        keys = [k for k, _ in entries]
        assert len(keys) == len(set(keys)), "duplicate keys found"


# ============================================================================
# Event Bus + Connectors integration  (P-09, P-10)
# ============================================================================


class TestEventBusConnectorsIntegration:
    """Cross-module tests: EnhancedBus + ConnectorEngine."""

    def test_wildcard_subscribe_and_deliver(self):
        """P-09/P-10: wildcard subscribers receive matching events."""
        bus = EnhancedBus()
        received = []
        bus.subscribe("stack.*", lambda e: received.append(e))
        event = create_event(EventType.STACK_PUSH, source="test")
        delivered = bus.publish(event)
        assert delivered == 1
        assert len(received) == 1
        assert received[0].event_type == EventType.STACK_PUSH

    def test_multiple_subscribers_all_receive(self):
        """P-09: all matching subscribers receive the event."""
        bus = EnhancedBus()
        r1, r2 = [], []
        bus.subscribe("stack.*", lambda e: r1.append(e))
        bus.subscribe("stack.push", lambda e: r2.append(e))
        event = create_event(EventType.STACK_PUSH, source="test")
        delivered = bus.publish(event)
        assert delivered == 2
        assert len(r1) == 1
        assert len(r2) == 1

    def test_non_matching_subscriber_not_called(self):
        """P-09: non-matching patterns are not delivered to."""
        bus = EnhancedBus()
        received = []
        bus.subscribe("pane.*", lambda e: received.append(e))
        event = create_event(EventType.STACK_PUSH, source="test")
        bus.publish(event)
        assert len(received) == 0

    def test_connector_engine_match_event_with_wildcard(self, tmp_path):
        """P-10: ConnectorEngine matches events with wildcard triggers."""
        cfile = tmp_path / "connectors.yaml"
        _write_yaml(str(cfile), {
            "connectors": [
                {
                    "name": "lint-on-save",
                    "trigger": {"type": "fs.*", "filter": {}},
                    "action": {"shell": "flake8"},
                },
                {
                    "name": "test-on-save",
                    "trigger": {
                        "type": "fs.file.saved",
                        "filter": {"pattern": "*.py"},
                    },
                    "action": {"shell": "pytest"},
                },
            ]
        })
        engine = ConnectorEngine()
        engine.load(str(cfile))
        matches = engine.match_event("fs.file.saved", {"pattern": "test.py"})
        names = [m.name for m in matches]
        assert "lint-on-save" in names
        assert "test-on-save" in names

    def test_connector_engine_get_action(self):
        """P-10: ConnectorEngine returns correct action descriptors."""
        c = ConnectorDef(name="test", trigger_type="evt", action_shell="pytest")
        engine = ConnectorEngine()
        action = engine.get_action(c)
        assert action == {"type": "shell", "command": "pytest"}

    def test_dead_subscriber_detection(self):
        """P-09: dead subscribers are detected after repeated failures."""
        bus = EnhancedBus()
        call_count = [0]

        def failing_callback(event):
            call_count[0] += 1
            raise RuntimeError("boom")

        bus.subscribe("stack.*", failing_callback)
        # Publish enough times to trigger dead detection (threshold = 3)
        for _ in range(4):
            bus.publish(create_event(EventType.STACK_PUSH, source="test"))
        dead = bus.dead_subscribers
        assert len(dead) == 1

    def test_event_history_records_all_published(self):
        """P-09: event history records all published events."""
        bus = EnhancedBus()
        bus.subscribe("*", lambda e: None)
        for etype in [EventType.STACK_PUSH, EventType.STACK_POP, EventType.STACK_ROTATE]:
            bus.publish(create_event(etype, source="test"))
        assert len(bus.history) == 3
        types = [e.event_type for e in bus.history]
        assert EventType.STACK_PUSH in types
        assert EventType.STACK_POP in types
        assert EventType.STACK_ROTATE in types

    def test_bus_publish_then_connector_match_pipeline(self, tmp_path):
        """P-09+P-10: event bus delivers event, connector engine matches it."""
        bus = EnhancedBus()
        matched_actions = []

        cfile = tmp_path / "connectors.yaml"
        _write_yaml(str(cfile), {
            "connectors": [{
                "name": "on-save",
                "trigger": {"type": "fs.file.saved"},
                "action": {"shell": "make lint"},
            }]
        })
        conn_engine = ConnectorEngine()
        conn_engine.load(str(cfile))

        def on_event(event):
            matches = conn_engine.match_event("fs.file.saved")
            for m in matches:
                matched_actions.append(conn_engine.get_action(m))

        bus.subscribe("workspace.*", on_event)
        bus.publish(create_event(EventType.WORKSPACE_SAVE, source="test"))
        assert len(matched_actions) == 1
        assert matched_actions[0]["command"] == "make lint"


# ============================================================================
# Full pipeline smoke tests  (multiple properties)
# ============================================================================


class TestFullPipelineSmoke:
    """End-to-end pipelines that exercise multiple modules together."""

    def test_detect_suggest_enable_profile_switch_pack_survives(self, tmp_path):
        """P-05/P-06/P-08: detect markers -> suggest -> enable -> profile switch -> pack still enabled."""
        # Set up packs
        pack_dir = tmp_path / "packs"
        pack_dir.mkdir()
        _write_yaml(str(pack_dir / "python.yaml"), {
            "name": "python", "markers": ["pyproject.toml"],
        })
        # Set up project with marker
        proj = tmp_path / "project"
        proj.mkdir()
        (proj / "pyproject.toml").touch()
        # Set up profiles
        prof_dir = tmp_path / "profiles"
        prof_dir.mkdir()
        _write_yaml(str(prof_dir / "work.yaml"), {"name": "work"})
        _write_yaml(str(prof_dir / "personal.yaml"), {"name": "personal"})

        pack_mgr = PackManager([str(pack_dir)])
        prof_mgr = ProfileManager(str(prof_dir))

        # Suggest packs (never auto-enable)
        suggestions = pack_mgr.suggest(str(proj))
        assert len(suggestions) == 1
        assert suggestions[0].enabled is False

        # User enables pack
        pack_mgr.enable("python")
        assert pack_mgr.get("python").enabled is True

        # Switch profile
        prof_mgr.switch("work")
        assert prof_mgr.active_profile.name == "work"

        # P-06: pack still enabled after profile switch
        assert pack_mgr.get("python").enabled is True

        # Switch again
        prof_mgr.switch("personal")
        assert pack_mgr.get("python").enabled is True

    def test_push_tabs_save_restore_tabs_match(self, tmp_path):
        """P-01/P-14: push -> save -> restore -> verify tabs."""
        mgr = _populated_manager()
        session_dir = str(tmp_path / "session")
        save_session(mgr, session_dir)

        mgr2 = StackManager()
        deferred = restore_session(mgr2, session_dir)

        # Verify stack structure matches
        orig_stacks = mgr.all_stacks()
        rest_stacks = mgr2.all_stacks()
        assert set(orig_stacks.keys()) == set(rest_stacks.keys())
        for pane_id in orig_stacks:
            assert len(orig_stacks[pane_id].tabs) == len(rest_stacks[pane_id].tabs)

    def test_graph_resolve_3_scopes_workspace_wins(self):
        """P-03: 3-scope resolution — workspace always wins."""
        g = [CommandGraphNode(id="cmd", label="Global", type=NodeType.ACTION)]
        p = [CommandGraphNode(id="cmd", label="Profile", type=NodeType.ACTION)]
        w = [CommandGraphNode(id="cmd", label="Workspace", type=NodeType.ACTION)]
        result = resolve_tree([g, p, w])
        assert result[0].label == "Workspace"

    def test_publish_event_connector_matches_action_returned(self, tmp_path):
        """P-09/P-10: publish event -> connector matches -> action returned."""
        cfile = tmp_path / "connectors.yaml"
        _write_yaml(str(cfile), {
            "connectors": [{
                "name": "auto-format",
                "trigger": {"type": "fs.file.saved"},
                "action": {"shell": "black ."},
            }]
        })
        conn_engine = ConnectorEngine()
        conn_engine.load(str(cfile))
        matches = conn_engine.match_event("fs.file.saved")
        assert len(matches) == 1
        action = conn_engine.get_action(matches[0])
        assert action["command"] == "black ."

    def test_all_engine_packages_importable(self):
        """Verify all engine __init__.py packages can be imported."""
        engine_root = os.path.join(PROJECT_ROOT, "core", "engine")
        failed = []
        for entry in sorted(os.listdir(engine_root)):
            pkg_dir = os.path.join(engine_root, entry)
            init_file = os.path.join(pkg_dir, "__init__.py")
            if os.path.isdir(pkg_dir) and os.path.isfile(init_file):
                mod_name = f"engine.{entry}"
                try:
                    _load_module(mod_name, os.path.relpath(init_file, PROJECT_ROOT))
                except Exception as exc:
                    failed.append((mod_name, str(exc)))
        assert failed == [], f"Failed to import: {failed}"
