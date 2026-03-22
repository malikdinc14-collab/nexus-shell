"""Tests for core/engine/profiles/manager.py — Profile model, ProfileManager,
profile-pack orthogonality (T045), and example profile loading."""

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Set

import pytest
import yaml

# ---------------------------------------------------------------------------
# Module loader (project convention)
# ---------------------------------------------------------------------------
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


manager_mod = _load_module(
    "profiles_manager", "core/engine/profiles/manager.py"
)
Profile = manager_mod.Profile
load_profile = manager_mod.load_profile
ProfileManager = manager_mod.ProfileManager

EXAMPLES_DIR = os.path.join(
    PROJECT_ROOT, "core", "engine", "profiles", "examples"
)

# ---------------------------------------------------------------------------
# Minimal mock PackManager for orthogonality tests (T045)
# ---------------------------------------------------------------------------


@dataclass
class MockPack:
    name: str
    tools: List[str] = field(default_factory=list)


class MockPackManager:
    """Lightweight stand-in that tracks enabled packs."""

    def __init__(self, packs: List[MockPack]) -> None:
        self._packs: Dict[str, MockPack] = {p.name: p for p in packs}
        self._enabled: Set[str] = set()

    def enable(self, name: str) -> bool:
        if name not in self._packs:
            return False
        self._enabled.add(name)
        return True

    def disable(self, name: str) -> bool:
        self._enabled.discard(name)
        return True

    @property
    def enabled_names(self) -> Set[str]:
        return set(self._enabled)

    def tools_for(self, name: str) -> List[str]:
        p = self._packs.get(name)
        return list(p.tools) if p else []


# ===================================================================
# Profile model tests
# ===================================================================


class TestProfileModel:
    def test_create_with_all_fields(self):
        p = Profile(
            name="full",
            description="all fields",
            composition="layout1",
            theme="dark",
            hud={"modules": ["clock"]},
            keybind_overrides={"Alt+x": "exit"},
            menu_nodes=[{"id": "m1"}],
            env={"FOO": "bar"},
        )
        assert p.name == "full"
        assert p.description == "all fields"
        assert p.composition == "layout1"
        assert p.theme == "dark"
        assert p.hud == {"modules": ["clock"]}
        assert p.keybind_overrides == {"Alt+x": "exit"}
        assert p.menu_nodes == [{"id": "m1"}]
        assert p.env == {"FOO": "bar"}

    def test_default_values(self):
        p = Profile(name="bare")
        assert p.description == ""
        assert p.composition is None
        assert p.theme is None
        assert p.hud == {}
        assert p.keybind_overrides == {}
        assert p.menu_nodes == []
        assert p.env == {}

    def test_load_profile_valid(self, tmp_path):
        data = {"name": "test", "theme": "monokai", "env": {"A": "1"}}
        f = tmp_path / "test.yaml"
        f.write_text(yaml.dump(data))
        p = load_profile(str(f))
        assert p is not None
        assert p.name == "test"
        assert p.theme == "monokai"
        assert p.env == {"A": "1"}

    def test_load_profile_missing_file(self):
        assert load_profile("/nonexistent/path/nope.yaml") is None

    def test_load_profile_invalid_yaml(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(": : : [invalid yaml{{{")
        assert load_profile(str(f)) is None

    def test_load_profile_missing_name_key(self, tmp_path):
        f = tmp_path / "noname.yaml"
        f.write_text(yaml.dump({"theme": "dark"}))
        assert load_profile(str(f)) is None


# ===================================================================
# ProfileManager tests
# ===================================================================


class TestProfileManager:
    @pytest.fixture()
    def profiles_dir(self, tmp_path):
        for name, comp in [("alpha", "c1"), ("beta", "c2")]:
            (tmp_path / f"{name}.yaml").write_text(
                yaml.dump({"name": name, "composition": comp})
            )
        return tmp_path

    def test_loads_profiles_from_directory(self, profiles_dir):
        pm = ProfileManager(str(profiles_dir))
        assert len(pm.available_profiles) == 2

    def test_available_profiles_returns_all(self, profiles_dir):
        pm = ProfileManager(str(profiles_dir))
        names = {p.name for p in pm.available_profiles}
        assert names == {"alpha", "beta"}

    def test_active_profile_starts_none(self, profiles_dir):
        pm = ProfileManager(str(profiles_dir))
        assert pm.active_profile is None

    def test_switch_activates_profile(self, profiles_dir):
        pm = ProfileManager(str(profiles_dir))
        assert pm.switch("alpha") is True
        assert pm.active_profile is not None
        assert pm.active_profile.name == "alpha"

    def test_switch_returns_false_for_unknown(self, profiles_dir):
        pm = ProfileManager(str(profiles_dir))
        assert pm.switch("nonexistent") is False

    def test_get_returns_profile(self, profiles_dir):
        pm = ProfileManager(str(profiles_dir))
        p = pm.get("beta")
        assert p is not None
        assert p.composition == "c2"

    def test_get_returns_none_for_unknown(self, profiles_dir):
        pm = ProfileManager(str(profiles_dir))
        assert pm.get("nope") is None

    def test_list_names(self, profiles_dir):
        pm = ProfileManager(str(profiles_dir))
        assert sorted(pm.list_names()) == ["alpha", "beta"]


# ===================================================================
# Profile-Pack orthogonality tests (T045)
# ===================================================================


class TestProfilePackOrthogonality:
    @pytest.fixture()
    def managers(self, tmp_path):
        for name, comp, theme in [
            ("dev", "layout-dev", "dark"),
            ("ops", "layout-ops", "light"),
        ]:
            (tmp_path / f"{name}.yaml").write_text(
                yaml.dump(
                    {
                        "name": name,
                        "composition": comp,
                        "theme": theme,
                        "env": {f"{name.upper()}_VAR": "1"},
                    }
                )
            )
        pm = ProfileManager(str(tmp_path))
        pack_mgr = MockPackManager(
            [
                MockPack("git", tools=["git-status", "git-log"]),
                MockPack("k8s", tools=["kubectl", "helm"]),
            ]
        )
        return pm, pack_mgr

    def test_switch_profile_does_not_touch_pack_enabled(self, managers):
        pm, packs = managers
        packs.enable("git")
        pm.switch("dev")
        assert packs.enabled_names == {"git"}

    def test_enable_pack_does_not_change_active_profile(self, managers):
        pm, packs = managers
        pm.switch("dev")
        packs.enable("k8s")
        assert pm.active_profile.name == "dev"

    def test_same_pack_different_profile_preserves_tools(self, managers):
        pm, packs = managers
        packs.enable("git")
        pm.switch("dev")
        tools_a = packs.tools_for("git")
        pm.switch("ops")
        tools_b = packs.tools_for("git")
        assert tools_a == tools_b

    def test_same_profile_different_pack_preserves_composition(self, managers):
        pm, packs = managers
        pm.switch("dev")
        packs.enable("git")
        comp_a = pm.active_profile.composition
        packs.disable("git")
        packs.enable("k8s")
        comp_b = pm.active_profile.composition
        assert comp_a == comp_b == "layout-dev"

    def test_double_switch_profile_is_clean(self, managers):
        pm, packs = managers
        packs.enable("git")
        pm.switch("dev")
        pm.switch("ops")
        pm.switch("dev")
        assert pm.active_profile.name == "dev"
        assert packs.enabled_names == {"git"}

    def test_profile_switch_preserves_env_independently(self, managers):
        pm, packs = managers
        packs.enable("k8s")
        pm.switch("dev")
        assert pm.active_profile.env == {"DEV_VAR": "1"}
        pm.switch("ops")
        assert pm.active_profile.env == {"OPS_VAR": "1"}
        # pack state unchanged
        assert packs.enabled_names == {"k8s"}

    def test_pack_enable_preserves_profile_theme(self, managers):
        pm, packs = managers
        pm.switch("dev")
        assert pm.active_profile.theme == "dark"
        packs.enable("git")
        packs.enable("k8s")
        assert pm.active_profile.theme == "dark"


# ===================================================================
# Example profile loading tests
# ===================================================================


class TestExampleProfiles:
    def test_devops_yaml_loads(self):
        p = load_profile(os.path.join(EXAMPLES_DIR, "devops.yaml"))
        assert p is not None
        assert p.name == "devops"
        assert p.composition == "devops"
        assert p.theme == "solarized-dark"
        assert "modules" in p.hud
        assert p.env.get("KUBECONFIG") == "~/.kube/config"

    def test_minimalist_yaml_loads(self):
        p = load_profile(os.path.join(EXAMPLES_DIR, "minimalist.yaml"))
        assert p is not None
        assert p.name == "minimalist"
        assert p.composition == "focused"
        assert p.theme == "catppuccin"
        assert p.hud.get("refresh_ms") == 5000
