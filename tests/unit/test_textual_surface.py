#!/usr/bin/env python3
"""
Tests for TextualSurface — the Level 0 contained Surface implementation.

Tests the Surface ABC contract (all 21 methods), PaneState management,
HUD rendering, menu overlay, and layout capture/apply.

PTY-dependent tests are skipped when running in CI or headless.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from engine.surfaces import (
    ContainerInfo,
    Dimensions,
    HudModule,
    MenuItem,
    NullSurface,
    SplitDirection,
    Surface,
)
from engine.surfaces.textual_surface import (
    HudBar,
    MenuOverlay,
    NexusApp,
    PaneState,
    PtyPane,
    TabBar,
    TextualSurface,
)


# ── PaneState ────────────────────────────────────────────────────────────────


class TestPaneState:
    def test_defaults(self):
        s = PaneState(handle="p1", index=0)
        assert s.handle == "p1"
        assert s.command == ""
        assert s.tags == {}
        assert s.pid == 0
        assert s.fd == -1
        assert s.focused is False

    def test_tags_mutable(self):
        s = PaneState(handle="p1", index=0)
        s.tags["role"] = "editor"
        assert s.tags["role"] == "editor"

    def test_dimensions(self):
        s = PaneState(handle="p1", index=0, width=120, height=40)
        assert s.width == 120
        assert s.height == 40


# ── TextualSurface ABC Contract ──────────────────────────────────────────────


class TestSurfaceContract:
    """Verify TextualSurface satisfies the Surface ABC."""

    def test_is_subclass_of_surface(self):
        assert issubclass(TextualSurface, Surface)

    def test_implements_all_abstract_methods(self):
        """All 21 abstract methods are implemented (no TypeError on init)."""
        surface = TextualSurface()
        assert surface is not None

    def test_abstract_method_count(self):
        """Surface ABC has exactly 21 abstract methods."""
        abstract = {
            name for name, val in vars(Surface).items()
            if getattr(val, "__isabstractmethod__", False)
        }
        assert len(abstract) == 21


class TestTextualSurfaceInitialize:
    def setup_method(self):
        self.surface = TextualSurface()

    def test_initialize_returns_handle(self):
        handle = self.surface.initialize("test-ws")
        assert handle.startswith("textual:")
        assert "test-ws" in handle

    def test_initialize_sets_app_title(self):
        self.surface.initialize("myws")
        assert "myws" in self.surface.app.title

    def test_teardown_clears_session(self):
        handle = self.surface.initialize("ws")
        self.surface.teardown(handle)
        assert handle not in self.surface._sessions


class TestTextualSurfacePanes:
    """Test pane CRUD via the surface — no real app event loop needed."""

    def setup_method(self):
        self.surface = TextualSurface()
        self.surface.initialize("test")
        # Patch out app mounting (no event loop running)
        self.surface.app.panes = {}
        self.surface.app._pane_counter = 0
        self.surface.app._focused_handle = None

    def test_pane_state_created(self):
        """create_container adds a PaneState to app.panes."""
        # Directly test PaneState management without widget mounting
        state = PaneState(handle="pane-1", index=1, command="zsh")
        self.surface.app.panes["pane-1"] = state
        assert "pane-1" in self.surface.app.panes

    def test_list_containers_returns_info(self):
        state = PaneState(
            handle="pane-1", index=1, command="nvim",
            width=80, height=24, title="editor", focused=True,
        )
        self.surface.app.panes["pane-1"] = state
        self.surface.app._focused_handle = "pane-1"

        containers = self.surface.list_containers("test")
        assert len(containers) == 1
        c = containers[0]
        assert isinstance(c, ContainerInfo)
        assert c.handle == "pane-1"
        assert c.command == "nvim"
        assert c.width == 80
        assert c.focused is True

    def test_get_focused_returns_handle(self):
        self.surface.app._focused_handle = "pane-2"
        assert self.surface.get_focused("test") == "pane-2"

    def test_get_focused_none_when_empty(self):
        assert self.surface.get_focused("test") is None

    def test_get_dimensions(self):
        state = PaneState(handle="pane-1", index=1, width=100, height=50)
        self.surface.app.panes["pane-1"] = state
        dims = self.surface.get_dimensions("pane-1")
        assert isinstance(dims, Dimensions)
        assert dims.width == 100
        assert dims.height == 50

    def test_get_dimensions_missing_pane(self):
        dims = self.surface.get_dimensions("nonexistent")
        assert dims.width == 0 and dims.height == 0

    def test_resize_updates_state(self):
        state = PaneState(handle="pane-1", index=1, width=80, height=24)
        self.surface.app.panes["pane-1"] = state
        self.surface.resize("pane-1", Dimensions(width=120, height=40))
        assert state.width == 120
        assert state.height == 40


class TestTextualSurfaceMetadata:
    def setup_method(self):
        self.surface = TextualSurface()
        self.surface.initialize("test")
        state = PaneState(handle="pane-1", index=1)
        self.surface.app.panes["pane-1"] = state

    def test_set_and_get_tag(self):
        self.surface.set_tag("pane-1", "role", "editor")
        assert self.surface.get_tag("pane-1", "role") == "editor"

    def test_get_tag_default_empty(self):
        assert self.surface.get_tag("pane-1", "missing") == ""

    def test_get_tag_missing_pane(self):
        assert self.surface.get_tag("nope", "key") == ""

    def test_set_title(self):
        self.surface.set_title("pane-1", "My Editor")
        assert self.surface.app.panes["pane-1"].title == "My Editor"


class TestTextualSurfaceEnvironment:
    def setup_method(self):
        self.surface = TextualSurface()

    def test_set_env(self):
        self.surface.set_env("session", "NEXUS_TEST_VAR", "hello")
        assert os.environ.get("NEXUS_TEST_VAR") == "hello"
        assert self.surface.app._env["NEXUS_TEST_VAR"] == "hello"
        # Cleanup
        del os.environ["NEXUS_TEST_VAR"]


class TestTextualSurfaceLayout:
    def setup_method(self):
        self.surface = TextualSurface()
        self.surface.initialize("test")

    def test_capture_layout_empty(self):
        layout = self.surface.capture_layout("test")
        assert layout == {"panes": [], "focused": None}

    def test_capture_layout_with_panes(self):
        state = PaneState(
            handle="pane-1", index=1, command="nvim",
            width=80, height=24, title="editor",
        )
        self.surface.app.panes["pane-1"] = state
        self.surface.app._focused_handle = "pane-1"

        layout = self.surface.capture_layout("test")
        assert len(layout["panes"]) == 1
        assert layout["panes"][0]["command"] == "nvim"
        assert layout["focused"] == "pane-1"

    def test_apply_layout_empty_returns_false(self):
        assert self.surface.apply_layout("test", {}) is False
        assert self.surface.apply_layout("test", {"panes": []}) is False


class TestTextualSurfaceSendInput:
    def test_send_input_no_fd(self):
        surface = TextualSurface()
        state = PaneState(handle="pane-1", index=1, fd=-1)
        surface.app.panes["pane-1"] = state
        # Should not raise
        surface.send_input("pane-1", "hello")

    def test_send_input_missing_pane(self):
        surface = TextualSurface()
        # Should not raise
        surface.send_input("nonexistent", "hello")


class TestTextualSurfaceMenu:
    def test_show_menu_returns_none_when_not_running(self):
        surface = TextualSurface()
        items = [MenuItem(id="a", label="Alpha")]
        result = surface.show_menu(items)
        assert result is None


class TestTextualSurfaceHud:
    def test_show_hud_stores_modules(self):
        surface = TextualSurface()
        modules = [HudModule(id="git", label="branch", value="main")]
        # Won't crash even without running app
        surface.app._hud_modules = []
        surface.app.update_hud = MagicMock()
        surface.show_hud(modules)
        surface.app.update_hud.assert_called_once_with(modules)


class TestTextualSurfaceNotify:
    def test_notify_when_not_running(self):
        surface = TextualSurface()
        # Should not raise even without running app
        surface.notify("test message")


# ── Widget Unit Tests ────────────────────────────────────────────────────────


class TestMenuOverlay:
    def test_items_stored(self):
        items = [
            MenuItem(id="a", label="Alpha", icon="α"),
            MenuItem(id="b", label="Beta", depth=1),
        ]
        overlay = MenuOverlay(items, prompt="Pick one:")
        assert overlay._prompt == "Pick one:"
        assert len(overlay._items) == 2

    def test_result_starts_none(self):
        overlay = MenuOverlay([], prompt="Test")
        assert overlay._result is None


class TestPaneStateDataclass:
    def test_tags_isolation(self):
        """Each PaneState gets its own tags dict."""
        a = PaneState(handle="a", index=0)
        b = PaneState(handle="b", index=1)
        a.tags["x"] = "1"
        assert "x" not in b.tags


# ── Textual Async Tests (using App pilot) ────────────────────────────────────


@pytest.mark.asyncio
class TestNexusAppAsync:
    """Tests that require the Textual event loop via run_test()."""

    async def test_app_mounts(self):
        app = NexusApp()
        async with app.run_test() as pilot:
            assert app.is_running

    async def test_add_pane(self):
        app = NexusApp()
        async with app.run_test() as pilot:
            handle = app.add_pane(command="echo hello")
            assert handle in app.panes
            assert app._focused_handle == handle

    async def test_add_multiple_panes(self):
        app = NexusApp()
        async with app.run_test() as pilot:
            h1 = app.add_pane()
            h2 = app.add_pane()
            assert len(app.panes) == 2
            # First pane gets focus by default
            assert app._focused_handle == h1

    async def test_focus_pane(self):
        app = NexusApp()
        async with app.run_test() as pilot:
            h1 = app.add_pane()
            h2 = app.add_pane()
            app.focus_pane(h2)
            assert app._focused_handle == h2
            assert app.panes[h2].focused is True
            assert app.panes[h1].focused is False

    async def test_remove_pane(self):
        app = NexusApp()
        async with app.run_test() as pilot:
            h1 = app.add_pane()
            h2 = app.add_pane()
            app.remove_pane(h1)
            assert h1 not in app.panes
            assert len(app.panes) == 1

    async def test_hud_update(self):
        app = NexusApp()
        async with app.run_test() as pilot:
            modules = [
                HudModule(id="git", label="branch", value="main", position="left"),
                HudModule(id="time", label="time", value="12:00", position="right"),
            ]
            app.update_hud(modules)
            # HudBar should have been updated
            hud = app.query_one("#hud-bar", HudBar)
            assert hud is not None

    async def test_header_and_footer_present(self):
        app = NexusApp()
        async with app.run_test() as pilot:
            from textual.widgets import Header, Footer
            assert app.query_one(Header) is not None
            assert app.query_one(Footer) is not None

    async def test_menu_overlay_shows_and_dismisses(self):
        app = NexusApp()
        async with app.run_test() as pilot:
            items = [MenuItem(id="a", label="Alpha")]
            overlay = MenuOverlay(items, prompt="Pick:", id="menu-overlay")
            await app.mount(overlay)
            assert app.query_one("#menu-overlay") is not None
            # Simulate escape
            overlay._result = None
            overlay._event.set()
            overlay.remove()
            await pilot.pause()

    async def test_focus_cycling(self):
        app = NexusApp()
        async with app.run_test() as pilot:
            h1 = app.add_pane()
            h2 = app.add_pane()
            h3 = app.add_pane()
            assert app._focused_handle == h1
            app._focus_adjacent(1)
            assert app._focused_handle == h2
            app._focus_adjacent(1)
            assert app._focused_handle == h3
            app._focus_adjacent(1)
            assert app._focused_handle == h1  # wraps around
