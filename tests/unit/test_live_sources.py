"""Tests for live source resolution and system root menu."""

import importlib.util
import sys
import os
import asyncio
import time

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


live_sources = _load_module("live_sources", "core/engine/graph/live_sources.py")


# ---------------------------------------------------------------------------
# LiveSourceRegistry tests
# ---------------------------------------------------------------------------

class TestLiveSourceRegistry:
    def test_register_and_get(self):
        reg = live_sources.LiveSourceRegistry()
        async def my_resolver():
            return "hello"
        reg.register("test.resolver", my_resolver)
        assert reg.get("test.resolver") is my_resolver

    def test_get_unregistered_returns_none(self):
        reg = live_sources.LiveSourceRegistry()
        assert reg.get("nonexistent.resolver") is None

    @pytest.mark.parametrize("name", [
        "nexus.live.current_composition",
        "nexus.live.current_profile",
        "nexus.live.suggested_packs",
        "nexus.live.enabled_packs",
        "nexus.live.active_tabs",
        "nexus.live.processes",
        "nexus.live.ports",
        "nexus.live.git_status",
        "nexus.live.connectors",
        "nexus.live.agent_status",
    ])
    def test_builtin_resolver_registered(self, name):
        reg = live_sources.LiveSourceRegistry()
        resolver = reg.get(name)
        assert resolver is not None, f"Built-in resolver '{name}' not registered"
        assert callable(resolver)


# ---------------------------------------------------------------------------
# resolve_live_source tests
# ---------------------------------------------------------------------------

class TestResolveLiveSource:
    def setup_method(self):
        live_sources.clear_cache()

    def test_resolves_successfully(self):
        result = asyncio.run(
            live_sources.resolve_live_source("node1", "nexus.live.git_status")
        )
        # Real resolver returns branch info or "(not a repo)"
        assert isinstance(result, str) and len(result) > 0

    def test_cached_result_within_ttl(self):
        """Second call should return cached result."""
        async def run():
            r1 = await live_sources.resolve_live_source(
                "n1", "nexus.live.git_status", cache_ttl_s=60
            )
            # Manually verify cache is populated
            assert "nexus.live.git_status" in live_sources._cache
            r2 = await live_sources.resolve_live_source(
                "n2", "nexus.live.git_status", cache_ttl_s=60
            )
            return r1, r2
        r1, r2 = asyncio.run(run())
        assert r1 == r2  # cached result must be identical

    def test_cache_expires_after_ttl(self):
        """Cache should expire after TTL."""
        call_count = 0

        async def counting_resolver():
            nonlocal call_count
            call_count += 1
            return f"result-{call_count}"

        live_sources._registry.register("test.counting", counting_resolver)
        try:
            async def run():
                r1 = await live_sources.resolve_live_source(
                    "n1", "test.counting", cache_ttl_s=0
                )
                # TTL=0 means cache is always expired
                r2 = await live_sources.resolve_live_source(
                    "n2", "test.counting", cache_ttl_s=0
                )
                return r1, r2
            r1, r2 = asyncio.run(run())
            assert r1 == "result-1"
            assert r2 == "result-2"
        finally:
            # Clean up
            live_sources._registry._resolvers.pop("test.counting", None)

    def test_timeout_returns_loading(self):
        async def slow_resolver():
            await asyncio.sleep(10)
            return "never"

        live_sources._registry.register("test.slow", slow_resolver)
        try:
            result = asyncio.run(
                live_sources.resolve_live_source("n1", "test.slow", timeout_ms=50)
            )
            assert result == "(loading...)"
        finally:
            live_sources._registry._resolvers.pop("test.slow", None)

    def test_error_returns_error(self):
        async def bad_resolver():
            raise ValueError("boom")

        live_sources._registry.register("test.bad", bad_resolver)
        try:
            result = asyncio.run(
                live_sources.resolve_live_source("n1", "test.bad")
            )
            assert result == "(error)"
        finally:
            live_sources._registry._resolvers.pop("test.bad", None)

    def test_unregistered_resolver_returns_error(self):
        result = asyncio.run(
            live_sources.resolve_live_source("n1", "nonexistent.resolver")
        )
        assert result == "(error)"


# ---------------------------------------------------------------------------
# resolve_all_live_sources tests
# ---------------------------------------------------------------------------

class TestResolveAllLiveSources:
    def setup_method(self):
        live_sources.clear_cache()

    def test_resolves_multiple_in_parallel(self):
        nodes = [
            {"node_id": "a", "resolver": "nexus.live.git_status"},
            {"node_id": "b", "resolver": "nexus.live.processes"},
            {"node_id": "c", "resolver": "nexus.live.ports"},
        ]
        results = asyncio.run(live_sources.resolve_all_live_sources(nodes))
        assert set(results.keys()) == {"a", "b", "c"}
        for v in results.values():
            assert isinstance(v, str) and len(v) > 0

    def test_handles_mix_of_success_and_timeout(self):
        async def slow():
            await asyncio.sleep(10)
            return "never"

        live_sources._registry.register("test.slow_mix", slow)
        try:
            nodes = [
                {"node_id": "ok", "resolver": "nexus.live.git_status", "timeout_ms": 3000},
                {"node_id": "slow", "resolver": "test.slow_mix", "timeout_ms": 50},
            ]
            results = asyncio.run(live_sources.resolve_all_live_sources(nodes))
            assert isinstance(results["ok"], str) and len(results["ok"]) > 0
            assert results["slow"] == "(loading...)"
        finally:
            live_sources._registry._resolvers.pop("test.slow_mix", None)

    def test_empty_list_returns_empty_dict(self):
        results = asyncio.run(live_sources.resolve_all_live_sources([]))
        assert results == {}


# ---------------------------------------------------------------------------
# system_root.yaml tests
# ---------------------------------------------------------------------------

class TestSystemRootYaml:
    @classmethod
    def setup_class(cls):
        import yaml
        yaml_path = os.path.join(PROJECT_ROOT, "core", "ui", "menus", "system_root.yaml")
        cls.yaml_path = yaml_path
        with open(yaml_path, "r") as f:
            cls.data = yaml.safe_load(f)

    def test_file_exists_and_valid_yaml(self):
        assert os.path.isfile(self.yaml_path)
        assert isinstance(self.data, list)

    def test_has_seven_top_level_groups(self):
        expected_ids = {"compositions", "profiles", "packs", "actions", "settings", "live", "custom"}
        actual_ids = {item["id"] for item in self.data}
        assert actual_ids == expected_ids
        assert len(self.data) == 7

    def test_settings_group_has_seven_children(self):
        settings = [g for g in self.data if g["id"] == "settings"][0]
        assert len(settings["children"]) == 7

    def test_live_group_has_six_children(self):
        live = [g for g in self.data if g["id"] == "live"][0]
        assert len(live["children"]) == 6

    def test_all_live_source_nodes_have_resolver(self):
        def walk(nodes):
            for node in nodes:
                if node.get("type") == "live_source":
                    assert "resolver" in node, f"Node {node.get('id')} missing resolver"
                if "children" in node and node["children"]:
                    walk(node["children"])
        walk(self.data)
