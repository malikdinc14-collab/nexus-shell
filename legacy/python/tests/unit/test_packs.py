"""Tests for the core.engine.packs package (T040-T044)."""
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

pack_mod = _load_module("engine.packs.pack", "core/engine/packs/pack.py")
detector_mod = _load_module("engine.packs.detector", "core/engine/packs/detector.py")
manager_mod = _load_module("engine.packs.manager", "core/engine/packs/manager.py")

Pack = pack_mod.Pack
load_pack_from_yaml = pack_mod.load_pack_from_yaml
detect_markers = detector_mod.detect_markers
suggest_packs = detector_mod.suggest_packs
PackManager = manager_mod.PackManager

EXAMPLES_DIR = os.path.join(PROJECT_ROOT, "core", "engine", "packs", "examples")


# ── Pack model tests ──────────────────────────────────────────────


class TestPackModel:
    def test_create_with_all_fields(self):
        p = Pack(
            name="test",
            version="2.0.0",
            description="desc",
            markers=["a.txt"],
            tools={"executor": "bash"},
            connectors=[{"name": "c"}],
            services=[{"name": "s"}],
            menu_nodes=[{"id": "m"}],
            actions=[{"id": "a"}],
            enabled=True,
        )
        assert p.name == "test"
        assert p.version == "2.0.0"
        assert p.description == "desc"
        assert p.markers == ["a.txt"]
        assert p.tools == {"executor": "bash"}
        assert p.connectors == [{"name": "c"}]
        assert p.services == [{"name": "s"}]
        assert p.menu_nodes == [{"id": "m"}]
        assert p.actions == [{"id": "a"}]
        assert p.enabled is True

    def test_default_values(self):
        p = Pack(name="minimal")
        assert p.version == "1.0.0"
        assert p.description == ""
        assert p.markers == []
        assert p.tools == {}
        assert p.connectors == []
        assert p.services == []
        assert p.menu_nodes == []
        assert p.actions == []
        assert p.enabled is False

    def test_load_pack_from_yaml_valid(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text(
            "name: hello\nversion: '2.0.0'\ndescription: hi\nmarkers: [a.txt]\n"
        )
        p = load_pack_from_yaml(str(f))
        assert p is not None
        assert p.name == "hello"
        assert p.version == "2.0.0"
        assert p.markers == ["a.txt"]

    def test_load_pack_from_yaml_missing_file(self):
        result = load_pack_from_yaml("/nonexistent/path/to/file.yaml")
        assert result is None

    def test_load_pack_from_yaml_invalid_yaml(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(":::invalid yaml{{{")
        # Even malformed YAML may parse; what matters is it doesn't crash
        result = load_pack_from_yaml(str(f))
        # Either None or a Pack with defaults is acceptable
        assert result is None or isinstance(result, Pack)

    def test_load_pack_from_yaml_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        p = load_pack_from_yaml(str(f))
        assert p is not None
        assert p.name == ""


# ── Detector tests ────────────────────────────────────────────────


class TestDetector:
    def test_detect_markers_finds_existing(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("")
        (tmp_path / "Dockerfile").write_text("")
        found = detect_markers(str(tmp_path))
        assert "pyproject.toml" in found
        assert "Dockerfile" in found

    def test_detect_markers_empty_for_clean_dir(self, tmp_path):
        found = detect_markers(str(tmp_path))
        assert found == []

    def test_detect_markers_nonexistent_dir(self):
        found = detect_markers("/nonexistent/dir/xyz")
        assert found == []

    def test_suggest_packs_matches_by_marker(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("")
        rust = Pack(name="rust", markers=["Cargo.toml"])
        python = Pack(name="python", markers=["pyproject.toml"])
        result = suggest_packs(str(tmp_path), [rust, python])
        assert len(result) == 1
        assert result[0].name == "rust"

    def test_suggest_packs_empty_when_no_match(self, tmp_path):
        p = Pack(name="rust", markers=["Cargo.toml"])
        result = suggest_packs(str(tmp_path), [p])
        assert result == []

    def test_suggest_packs_sorts_by_match_count(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("")
        (tmp_path / "setup.py").write_text("")
        (tmp_path / "Cargo.toml").write_text("")
        python = Pack(name="python", markers=["pyproject.toml", "setup.py"])
        rust = Pack(name="rust", markers=["Cargo.toml"])
        result = suggest_packs(str(tmp_path), [rust, python])
        assert result[0].name == "python"  # 2 matches
        assert result[1].name == "rust"    # 1 match

    def test_suggest_packs_never_enables(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("")
        p = Pack(name="rust", markers=["Cargo.toml"], enabled=False)
        result = suggest_packs(str(tmp_path), [p])
        assert len(result) == 1
        assert result[0].enabled is False


# ── PackManager tests ─────────────────────────────────────────────


class TestPackManager:
    def _make_pack_dir(self, tmp_path, packs):
        """Write pack YAML files into tmp_path, return the dir path."""
        d = tmp_path / "packs"
        d.mkdir()
        for name, content in packs.items():
            (d / f"{name}.yaml").write_text(content)
        return str(d)

    def test_loads_packs_from_directory(self, tmp_path):
        d = self._make_pack_dir(tmp_path, {
            "a": "name: alpha\nversion: '1.0.0'\n",
            "b": "name: beta\nversion: '1.0.0'\n",
        })
        mgr = PackManager([d])
        assert len(mgr.available_packs) == 2

    def test_available_packs_returns_all(self, tmp_path):
        d = self._make_pack_dir(tmp_path, {
            "a": "name: alpha\n",
            "b": "name: beta\nenabled: true\n",
        })
        mgr = PackManager([d])
        assert len(mgr.available_packs) == 2

    def test_enabled_packs_returns_only_enabled(self, tmp_path):
        d = self._make_pack_dir(tmp_path, {
            "a": "name: alpha\nenabled: true\n",
            "b": "name: beta\n",
        })
        mgr = PackManager([d])
        enabled = mgr.enabled_packs
        assert len(enabled) == 1
        assert enabled[0].name == "alpha"

    def test_enable_enables_pack(self, tmp_path):
        d = self._make_pack_dir(tmp_path, {"a": "name: alpha\n"})
        mgr = PackManager([d])
        assert mgr.enable("alpha") is True
        assert mgr.get("alpha").enabled is True

    def test_enable_idempotent(self, tmp_path):
        d = self._make_pack_dir(tmp_path, {"a": "name: alpha\nenabled: true\n"})
        mgr = PackManager([d])
        assert mgr.enable("alpha") is True
        assert mgr.get("alpha").enabled is True

    def test_enable_returns_false_for_unknown(self, tmp_path):
        mgr = PackManager([str(tmp_path)])
        assert mgr.enable("nonexistent") is False

    def test_disable_disables_pack(self, tmp_path):
        d = self._make_pack_dir(tmp_path, {"a": "name: alpha\nenabled: true\n"})
        mgr = PackManager([d])
        assert mgr.disable("alpha") is True
        assert mgr.get("alpha").enabled is False

    def test_disable_idempotent(self, tmp_path):
        d = self._make_pack_dir(tmp_path, {"a": "name: alpha\n"})
        mgr = PackManager([d])
        assert mgr.disable("alpha") is True
        assert mgr.get("alpha").enabled is False

    def test_get_returns_pack_by_name(self, tmp_path):
        d = self._make_pack_dir(tmp_path, {"a": "name: alpha\n"})
        mgr = PackManager([d])
        p = mgr.get("alpha")
        assert p is not None
        assert p.name == "alpha"

    def test_get_returns_none_for_unknown(self, tmp_path):
        mgr = PackManager([str(tmp_path)])
        assert mgr.get("nope") is None

    def test_suggest_delegates_to_detector(self, tmp_path):
        d = self._make_pack_dir(tmp_path, {
            "py": "name: python\nmarkers: [pyproject.toml]\n",
        })
        project = tmp_path / "project"
        project.mkdir()
        (project / "pyproject.toml").write_text("")
        mgr = PackManager([d])
        suggestions = mgr.suggest(str(project))
        assert len(suggestions) == 1
        assert suggestions[0].name == "python"

    def test_skips_nonexistent_directory(self):
        mgr = PackManager(["/nonexistent/dir/xyz"])
        assert mgr.available_packs == []


# ── Example pack tests ────────────────────────────────────────────


class TestExamplePacks:
    def test_python_yaml_loads(self):
        p = load_pack_from_yaml(os.path.join(EXAMPLES_DIR, "python.yaml"))
        assert p is not None
        assert p.name == "python"
        assert p.version == "1.0.0"
        assert p.description == "Python development pack"

    def test_rust_yaml_loads(self):
        p = load_pack_from_yaml(os.path.join(EXAMPLES_DIR, "rust.yaml"))
        assert p is not None
        assert p.name == "rust"
        assert p.version == "1.0.0"

    def test_docker_yaml_loads(self):
        p = load_pack_from_yaml(os.path.join(EXAMPLES_DIR, "docker.yaml"))
        assert p is not None
        assert p.name == "docker"
        assert p.version == "1.0.0"

    def test_all_packs_have_markers(self):
        for fname in ("python.yaml", "rust.yaml", "docker.yaml"):
            p = load_pack_from_yaml(os.path.join(EXAMPLES_DIR, fname))
            assert p is not None
            assert len(p.markers) > 0, f"{fname} has no markers"

    def test_all_packs_have_menu_nodes(self):
        for fname in ("python.yaml", "rust.yaml", "docker.yaml"):
            p = load_pack_from_yaml(os.path.join(EXAMPLES_DIR, fname))
            assert p is not None
            assert len(p.menu_nodes) > 0, f"{fname} has no menu_nodes"
