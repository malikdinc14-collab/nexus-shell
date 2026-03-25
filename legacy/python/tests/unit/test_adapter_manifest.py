#!/usr/bin/env python3
"""
Tests for AdapterManifest, NullMenuAdapter, and manifest-aware registry.
========================================================================
Covers T003 (AdapterManifest on all adapters) and T004 (NullMenuAdapter).
"""

import sys
import os
from unittest.mock import patch
from io import StringIO

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from core.engine.capabilities.base import (
    AdapterManifest,
    CapabilityType,
)
from core.engine.capabilities.adapters.menu.null_menu import NullMenuAdapter


# ---------------------------------------------------------------------------
# AdapterManifest.is_available()
# ---------------------------------------------------------------------------

class TestAdapterManifestAvailability:
    """Test manifest.is_available() with real and fake binaries."""

    def test_real_binary_is_available(self):
        """'true' exists on every POSIX system."""
        m = AdapterManifest(
            name="test-real",
            capability_type=CapabilityType.MENU,
            binary="true",
        )
        assert m.is_available() is True

    def test_fake_binary_is_not_available(self):
        m = AdapterManifest(
            name="test-fake",
            capability_type=CapabilityType.MENU,
            binary="__nonexistent_binary_abc123__",
        )
        assert m.is_available() is False

    def test_no_binary_means_always_available(self):
        """Adapters with no binary (like textual) report available by default."""
        m = AdapterManifest(
            name="test-no-binary",
            capability_type=CapabilityType.MENU,
        )
        assert m.is_available() is True

    def test_binary_candidates_fallback(self):
        """If primary binary is missing, candidates are checked."""
        m = AdapterManifest(
            name="test-candidates",
            capability_type=CapabilityType.MENU,
            binary="__nonexistent__",
            binary_candidates=["__also_nonexistent__", "true"],
        )
        assert m.is_available() is True

    def test_all_candidates_missing(self):
        m = AdapterManifest(
            name="test-all-missing",
            capability_type=CapabilityType.MENU,
            binary="__nope_a__",
            binary_candidates=["__nope_b__", "__nope_c__"],
        )
        assert m.is_available() is False


# ---------------------------------------------------------------------------
# NullMenuAdapter
# ---------------------------------------------------------------------------

class TestNullMenuAdapter:
    """Test the always-available stdin fallback menu."""

    def test_is_always_available(self):
        adapter = NullMenuAdapter()
        assert adapter.is_available() is True

    def test_manifest_exists_and_is_lowest_priority(self):
        adapter = NullMenuAdapter()
        assert adapter.manifest is not None
        assert adapter.manifest.name == "null-menu"
        assert adapter.manifest.priority == 0
        assert adapter.manifest.capability_type == CapabilityType.MENU

    def test_capability_type_is_menu(self):
        adapter = NullMenuAdapter()
        assert adapter.capability_type == CapabilityType.MENU

    def test_show_menu_returns_valid_selection(self):
        adapter = NullMenuAdapter()
        options = ["alpha", "beta", "gamma"]
        # Simulate user typing "2" (selects "beta")
        with patch("builtins.input", return_value="2"):
            result = adapter.show_menu(options, "Pick one:")
        assert result == "beta"

    def test_show_menu_returns_none_on_invalid_input(self):
        adapter = NullMenuAdapter()
        options = ["alpha", "beta"]
        with patch("builtins.input", return_value="bad"):
            result = adapter.show_menu(options)
        assert result is None

    def test_show_menu_returns_none_on_out_of_range(self):
        adapter = NullMenuAdapter()
        options = ["alpha", "beta"]
        with patch("builtins.input", return_value="99"):
            result = adapter.show_menu(options)
        assert result is None

    def test_show_menu_returns_none_on_empty_options(self):
        adapter = NullMenuAdapter()
        result = adapter.show_menu([])
        assert result is None

    def test_show_menu_handles_eof(self):
        adapter = NullMenuAdapter()
        with patch("builtins.input", side_effect=EOFError):
            result = adapter.show_menu(["a", "b"])
        assert result is None

    def test_pick_delegates_to_show_menu(self):
        adapter = NullMenuAdapter()
        items = ["item_a", "item_b"]
        with patch("builtins.input", return_value="1"):
            result = adapter.pick("context", items)
        assert result == "item_a"


# ---------------------------------------------------------------------------
# Registry: manifest-aware priority sorting
# ---------------------------------------------------------------------------

class TestRegistryManifestPriority:
    """Test that the registry returns the highest-priority adapter."""

    def test_get_best_returns_highest_priority(self):
        """Build a fresh registry and verify priority ordering."""
        from core.engine.capabilities.registry import CapabilityRegistry

        # Build registry — it auto-registers adapters
        registry = CapabilityRegistry()

        # NullMenuAdapter should always be registered
        menu_adapters = registry.list_all(CapabilityType.MENU)
        null_adapters = [
            a for a in menu_adapters
            if isinstance(a, NullMenuAdapter)
        ]
        assert len(null_adapters) >= 1, "NullMenuAdapter must be auto-registered"

    def test_null_menu_is_last_resort(self):
        """NullMenuAdapter has the lowest priority among MENU adapters."""
        from core.engine.capabilities.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        best = registry.get_best(CapabilityType.MENU)

        # If any real menu tool is available, best should NOT be NullMenuAdapter.
        # If no real menu tool is available, best IS NullMenuAdapter.
        menu_adapters = registry.list_all(CapabilityType.MENU)
        real_adapters = [
            a for a in menu_adapters
            if not isinstance(a, NullMenuAdapter) and a.is_available()
        ]
        if real_adapters:
            assert not isinstance(best, NullMenuAdapter), (
                "NullMenuAdapter should not be best when real adapters exist"
            )
        else:
            assert isinstance(best, NullMenuAdapter), (
                "NullMenuAdapter should be best when no real adapters exist"
            )

    def test_list_all_with_manifests(self):
        """list_all_with_manifests returns tuples of (adapter, manifest)."""
        from core.engine.capabilities.registry import CapabilityRegistry

        registry = CapabilityRegistry()
        pairs = registry.list_all_with_manifests(CapabilityType.MENU)
        assert len(pairs) >= 1
        for adapter, manifest in pairs:
            assert hasattr(adapter, "is_available")
            # manifest may be None for legacy adapters, but all current ones have it
            if manifest is not None:
                assert isinstance(manifest, AdapterManifest)

    def test_priority_sorting_synthetic(self):
        """Directly verify that get_best picks by priority, not insertion order."""
        from core.engine.capabilities.base import Capability, MenuCapability
        from core.engine.capabilities.registry import CapabilityRegistry

        class LowPriorityMenu(MenuCapability):
            manifest = AdapterManifest(
                name="low", capability_type=CapabilityType.MENU, priority=10,
            )
            @property
            def capability_id(self): return "low"
            def is_available(self): return True
            def show_menu(self, options, prompt="Select:"): return None
            def pick(self, context, items_json): return None

        class HighPriorityMenu(MenuCapability):
            manifest = AdapterManifest(
                name="high", capability_type=CapabilityType.MENU, priority=200,
            )
            @property
            def capability_id(self): return "high"
            def is_available(self): return True
            def show_menu(self, options, prompt="Select:"): return None
            def pick(self, context, items_json): return None

        # Build empty registry (skip auto-register by patching)
        with patch.object(CapabilityRegistry, "_auto_register"):
            registry = CapabilityRegistry()

        # Register low first, then high — get_best should still return high
        registry.register(LowPriorityMenu())
        registry.register(HighPriorityMenu())

        best = registry.get_best(CapabilityType.MENU)
        assert best.manifest.name == "high"


# ---------------------------------------------------------------------------
# Existing adapters have manifests
# ---------------------------------------------------------------------------

class TestAllAdaptersHaveManifests:
    """Every adapter that ships with nexus-shell must declare a manifest."""

    def test_fzf_manifest(self):
        from core.engine.capabilities.adapters.menu.fzf_menu import FzfMenuAdapter
        assert FzfMenuAdapter.manifest is not None
        assert FzfMenuAdapter.manifest.name == "fzf"
        assert FzfMenuAdapter.manifest.binary == "fzf"

    def test_gum_manifest(self):
        from core.engine.capabilities.adapters.menu.gum_menu import GumMenuAdapter
        assert GumMenuAdapter.manifest is not None
        assert GumMenuAdapter.manifest.name == "gum"
        assert GumMenuAdapter.manifest.priority == 80

    def test_textual_manifest(self):
        from core.engine.capabilities.adapters.menu.textual_menu import TextualMenuAdapter
        assert TextualMenuAdapter.manifest is not None
        assert TextualMenuAdapter.manifest.name == "textual"
        assert TextualMenuAdapter.manifest.priority == 60

    def test_neovim_manifest(self):
        from core.engine.capabilities.adapters.editor.neovim import NeovimAdapter
        assert NeovimAdapter.manifest is not None
        assert NeovimAdapter.manifest.name == "neovim"
        assert NeovimAdapter.manifest.native_multiplicity is True

    def test_yazi_manifest(self):
        from core.engine.capabilities.adapters.explorer.yazi import YaziAdapter
        assert YaziAdapter.manifest is not None
        assert YaziAdapter.manifest.name == "yazi"

    def test_opencode_manifest(self):
        from core.engine.capabilities.adapters.agent.opencode import OpenCodeAdapter
        assert OpenCodeAdapter.manifest is not None
        assert OpenCodeAdapter.manifest.name == "opencode"

    def test_null_multiplexer_manifest(self):
        from core.engine.capabilities.adapters.multiplexer.null import NullAdapter
        assert NullAdapter.manifest is not None
        assert NullAdapter.manifest.name == "null-multiplexer"
        assert NullAdapter.manifest.priority == 0

    def test_tmux_manifest(self):
        from core.engine.capabilities.adapters.multiplexer.tmux import TmuxAdapter
        assert TmuxAdapter.manifest is not None
        assert TmuxAdapter.manifest.name == "tmux"
        assert TmuxAdapter.manifest.binary == "tmux"
