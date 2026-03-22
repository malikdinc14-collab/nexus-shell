"""Tests for core/engine/connectors/engine.py — ConnectorDef, loader, and ConnectorEngine."""

import importlib.util
import os
import sys

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


engine_mod = _load_module("connectors_engine", "core/engine/connectors/engine.py")
ConnectorDef = engine_mod.ConnectorDef
load_connectors_from_yaml = engine_mod.load_connectors_from_yaml
ConnectorEngine = engine_mod.ConnectorEngine


# ---------------------------------------------------------------------------
# ConnectorDef dataclass
# ---------------------------------------------------------------------------


class TestConnectorDef:
    def test_create_with_all_fields(self):
        c = ConnectorDef(
            name="lint",
            trigger_type="fs.file.saved",
            trigger_filter={"pattern": "*.py"},
            action_shell="flake8",
            action_internal=None,
            scope="workspace",
            enabled=False,
        )
        assert c.name == "lint"
        assert c.trigger_type == "fs.file.saved"
        assert c.trigger_filter == {"pattern": "*.py"}
        assert c.action_shell == "flake8"
        assert c.action_internal is None
        assert c.scope == "workspace"
        assert c.enabled is False

    def test_default_values(self):
        c = ConnectorDef(name="x", trigger_type="evt")
        assert c.trigger_filter == {}
        assert c.action_shell is None
        assert c.action_internal is None
        assert c.scope == "global"
        assert c.enabled is True


# ---------------------------------------------------------------------------
# load_connectors_from_yaml
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path, data, filename="connectors.yaml"):
    p = tmp_path / filename
    p.write_text(yaml.dump(data))
    return str(p)


class TestLoadConnectorsFromYaml:
    def test_loads_valid_file(self, tmp_path):
        path = _write_yaml(tmp_path, {
            "connectors": [
                {
                    "name": "test-on-save",
                    "trigger": {"type": "fs.file.saved", "filter": {"pattern": "*.py"}},
                    "action": {"shell": "pytest"},
                    "scope": "workspace",
                }
            ]
        })
        result = load_connectors_from_yaml(path)
        assert len(result) == 1
        assert result[0].name == "test-on-save"

    def test_returns_empty_for_missing_file(self):
        assert load_connectors_from_yaml("/nonexistent/path.yaml") == []

    def test_returns_empty_for_invalid_yaml(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(": : : not valid yaml [[[")
        assert load_connectors_from_yaml(str(p)) == []

    def test_parses_trigger_type(self, tmp_path):
        path = _write_yaml(tmp_path, {
            "connectors": [
                {"name": "a", "trigger": {"type": "git.commit"}, "action": {"shell": "echo"}}
            ]
        })
        result = load_connectors_from_yaml(path)
        assert result[0].trigger_type == "git.commit"

    def test_parses_trigger_filter(self, tmp_path):
        path = _write_yaml(tmp_path, {
            "connectors": [
                {"name": "a", "trigger": {"type": "x", "filter": {"ext": ".rs"}}, "action": {"shell": "cargo test"}}
            ]
        })
        result = load_connectors_from_yaml(path)
        assert result[0].trigger_filter == {"ext": ".rs"}

    def test_parses_shell_action(self, tmp_path):
        path = _write_yaml(tmp_path, {
            "connectors": [
                {"name": "a", "trigger": {"type": "x"}, "action": {"shell": "make build"}}
            ]
        })
        result = load_connectors_from_yaml(path)
        assert result[0].action_shell == "make build"
        assert result[0].action_internal is None

    def test_parses_internal_action(self, tmp_path):
        path = _write_yaml(tmp_path, {
            "connectors": [
                {"name": "a", "trigger": {"type": "x"}, "action": {"internal": "nexus-ctl reload"}}
            ]
        })
        result = load_connectors_from_yaml(path)
        assert result[0].action_internal == "nexus-ctl reload"
        assert result[0].action_shell is None


# ---------------------------------------------------------------------------
# ConnectorEngine
# ---------------------------------------------------------------------------


def _make_yaml(tmp_path, connectors, filename="connectors.yaml"):
    return _write_yaml(tmp_path, {"connectors": connectors}, filename)


class TestConnectorEngine:
    def test_load_adds_connectors(self, tmp_path):
        path = _make_yaml(tmp_path, [
            {"name": "c1", "trigger": {"type": "e1"}, "action": {"shell": "cmd1"}},
            {"name": "c2", "trigger": {"type": "e2"}, "action": {"shell": "cmd2"}},
        ])
        eng = ConnectorEngine()
        eng.load(path)
        assert len(eng.all_connectors) == 2

    def test_load_cascade_merges(self, tmp_path):
        gdir = tmp_path / "global"
        gdir.mkdir()
        wdir = tmp_path / "ws"
        wdir.mkdir()
        _write_yaml(gdir, {"connectors": [
            {"name": "g1", "trigger": {"type": "e1"}, "action": {"shell": "gcmd"}},
        ]})
        _write_yaml(wdir, {"connectors": [
            {"name": "w1", "trigger": {"type": "e2"}, "action": {"shell": "wcmd"}},
        ]})
        eng = ConnectorEngine()
        eng.load_cascade(str(gdir), str(wdir))
        names = {c.name for c in eng.all_connectors}
        assert names == {"g1", "w1"}

    def test_load_cascade_workspace_overrides_by_name(self, tmp_path):
        gdir = tmp_path / "global"
        gdir.mkdir()
        wdir = tmp_path / "ws"
        wdir.mkdir()
        _write_yaml(gdir, {"connectors": [
            {"name": "shared", "trigger": {"type": "e1"}, "action": {"shell": "global-cmd"}},
        ]})
        _write_yaml(wdir, {"connectors": [
            {"name": "shared", "trigger": {"type": "e1"}, "action": {"shell": "ws-cmd"}},
        ]})
        eng = ConnectorEngine()
        eng.load_cascade(str(gdir), str(wdir))
        assert len(eng.all_connectors) == 1
        assert eng.all_connectors[0].action_shell == "ws-cmd"

    def test_match_event_returns_matching(self, tmp_path):
        path = _make_yaml(tmp_path, [
            {"name": "m1", "trigger": {"type": "fs.file.saved"}, "action": {"shell": "echo"}},
            {"name": "m2", "trigger": {"type": "git.push"}, "action": {"shell": "echo"}},
        ])
        eng = ConnectorEngine()
        eng.load(path)
        matched = eng.match_event("fs.file.saved")
        assert len(matched) == 1
        assert matched[0].name == "m1"

    def test_match_event_with_filter_match(self, tmp_path):
        path = _make_yaml(tmp_path, [
            {"name": "f1", "trigger": {"type": "fs.file.saved", "filter": {"pattern": "*.py"}}, "action": {"shell": "pytest"}},
        ])
        eng = ConnectorEngine()
        eng.load(path)
        matched = eng.match_event("fs.file.saved", {"pattern": "test.py"})
        assert len(matched) == 1

    def test_match_event_with_filter_mismatch(self, tmp_path):
        path = _make_yaml(tmp_path, [
            {"name": "f1", "trigger": {"type": "fs.file.saved", "filter": {"pattern": "*.py"}}, "action": {"shell": "pytest"}},
        ])
        eng = ConnectorEngine()
        eng.load(path)
        matched = eng.match_event("fs.file.saved", {"pattern": "readme.md"})
        assert len(matched) == 0

    def test_match_event_wildcard_trigger(self, tmp_path):
        path = _make_yaml(tmp_path, [
            {"name": "w1", "trigger": {"type": "fs.*"}, "action": {"shell": "echo"}},
        ])
        eng = ConnectorEngine()
        eng.load(path)
        assert len(eng.match_event("fs.file.saved")) == 1
        assert len(eng.match_event("fs.dir.created")) == 1
        assert len(eng.match_event("git.push")) == 0

    def test_match_event_no_match(self, tmp_path):
        path = _make_yaml(tmp_path, [
            {"name": "n1", "trigger": {"type": "git.push"}, "action": {"shell": "echo"}},
        ])
        eng = ConnectorEngine()
        eng.load(path)
        assert eng.match_event("fs.file.saved") == []

    def test_get_action_shell(self):
        c = ConnectorDef(name="x", trigger_type="e", action_shell="make test")
        eng = ConnectorEngine()
        assert eng.get_action(c) == {"type": "shell", "command": "make test"}

    def test_get_action_internal(self):
        c = ConnectorDef(name="x", trigger_type="e", action_internal="nexus-ctl reload")
        eng = ConnectorEngine()
        assert eng.get_action(c) == {"type": "internal", "command": "nexus-ctl reload"}

    def test_all_connectors_returns_all(self, tmp_path):
        path = _make_yaml(tmp_path, [
            {"name": "a", "trigger": {"type": "e"}, "action": {"shell": "x"}, "enabled": True},
            {"name": "b", "trigger": {"type": "e"}, "action": {"shell": "y"}, "enabled": False},
        ])
        eng = ConnectorEngine()
        eng.load(path)
        assert len(eng.all_connectors) == 2

    def test_enabled_connectors_filters_disabled(self, tmp_path):
        path = _make_yaml(tmp_path, [
            {"name": "a", "trigger": {"type": "e"}, "action": {"shell": "x"}, "enabled": True},
            {"name": "b", "trigger": {"type": "e"}, "action": {"shell": "y"}, "enabled": False},
        ])
        eng = ConnectorEngine()
        eng.load(path)
        enabled = eng.enabled_connectors
        assert len(enabled) == 1
        assert enabled[0].name == "a"

    def test_disabled_connector_not_matched(self, tmp_path):
        path = _make_yaml(tmp_path, [
            {"name": "d1", "trigger": {"type": "fs.file.saved"}, "action": {"shell": "x"}, "enabled": False},
        ])
        eng = ConnectorEngine()
        eng.load(path)
        assert eng.match_event("fs.file.saved") == []
