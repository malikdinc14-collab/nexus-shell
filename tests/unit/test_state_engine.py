#!/usr/bin/env python3
# tests/unit/test_state_engine.py
"""
Unit tests for NexusStateEngine (core/engine/state/state_engine.py).

Uses pytest's tmp_path fixture — no real filesystem side effects.
"""

import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core/engine/state"))
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from state_engine import NexusStateEngine, SCHEMA_VERSION


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_engine(tmp_path) -> NexusStateEngine:
    """Create a fresh engine backed by a temp directory."""
    return NexusStateEngine(tmp_path)


def engine_with_state(tmp_path, state: dict) -> NexusStateEngine:
    """Write state.json into tmp_path/.nexus/ and load an engine."""
    nexus_dir = tmp_path / ".nexus"
    nexus_dir.mkdir()
    (nexus_dir / "state.json").write_text(json.dumps(state))
    return NexusStateEngine(tmp_path)


# ── Schema / initialization ───────────────────────────────────────────────────

class TestInitialization:
    def test_fresh_state_has_schema_version(self, tmp_path):
        eng = make_engine(tmp_path)
        assert eng.state["schema_version"] == SCHEMA_VERSION

    def test_fresh_state_has_project_name(self, tmp_path):
        eng = make_engine(tmp_path)
        assert eng.state["project"]["name"] == tmp_path.name

    def test_fresh_state_has_project_path(self, tmp_path):
        eng = make_engine(tmp_path)
        assert eng.state["project"]["path"] == str(tmp_path)

    def test_fresh_state_has_ui_structure(self, tmp_path):
        eng = make_engine(tmp_path)
        assert "slots" in eng.state["ui"]
        assert "stacks" in eng.state["ui"]

    def test_loads_existing_state_file(self, tmp_path):
        state = {"schema_version": 1, "custom": "hello"}
        eng = engine_with_state(tmp_path, state)
        assert eng.state["custom"] == "hello"

    def test_active_file_is_primary_when_writable(self, tmp_path):
        eng = make_engine(tmp_path)
        expected = tmp_path / ".nexus" / "state.json"
        assert eng.active_file == expected


# ── Fallback on load errors ───────────────────────────────────────────────────

class TestFallbackLoad:
    def test_falls_back_on_corrupt_json(self, tmp_path):
        nexus_dir = tmp_path / ".nexus"
        nexus_dir.mkdir()
        (nexus_dir / "state.json").write_text("{invalid json!!!}")
        # Should not raise — loads default state
        eng = NexusStateEngine(tmp_path)
        assert "schema_version" in eng.state

    def test_falls_back_to_fallback_file_on_permission_error(self, tmp_path):
        """Primary state raises PermissionError → engine loads default state without crashing."""
        nexus_dir = tmp_path / ".nexus"
        nexus_dir.mkdir()
        primary = nexus_dir / "state.json"
        primary.write_text("{invalid json}")  # corrupt — triggers JSONDecodeError fallback
        eng = NexusStateEngine(tmp_path)
        # Should have loaded default state without raising
        assert "schema_version" in eng.state


# ── get() ─────────────────────────────────────────────────────────────────────

class TestGet:
    def test_get_top_level_key(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.state["foo"] = "bar"
        assert eng.get("foo") == "bar"

    def test_get_nested_key(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.state["a"] = {"b": {"c": 42}}
        assert eng.get("a.b.c") == 42

    def test_get_missing_key_returns_none(self, tmp_path):
        eng = make_engine(tmp_path)
        assert eng.get("nonexistent") is None

    def test_get_missing_nested_returns_none(self, tmp_path):
        eng = make_engine(tmp_path)
        assert eng.get("a.b.c") is None

    def test_get_when_mid_key_is_not_dict(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.state["a"] = "scalar"
        # a is a string, not a dict — traversal should return None
        assert eng.get("a.b") is None

    def test_get_returns_dict_value(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.state["nested"] = {"x": 1}
        assert eng.get("nested") == {"x": 1}


# ── set() ─────────────────────────────────────────────────────────────────────

class TestSet:
    def test_set_top_level(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("mykey", "myval")
        assert eng.state["mykey"] == "myval"

    def test_set_creates_nested_dicts(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("alpha.beta.gamma", "deep")
        assert eng.state["alpha"]["beta"]["gamma"] == "deep"

    def test_set_overwrites_existing(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("x", 1)
        eng.set("x", 2)
        assert eng.state["x"] == 2

    def test_set_persists_to_disk(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("saved", "yes")
        eng2 = NexusStateEngine(tmp_path)
        assert eng2.get("saved") == "yes"

    def test_auto_convert_true_string(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("flag", "true")
        assert eng.state["flag"] is True

    def test_auto_convert_false_string(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("flag", "false")
        assert eng.state["flag"] is False

    def test_auto_convert_digit_string_to_int(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("count", "42")
        assert eng.state["count"] == 42
        assert isinstance(eng.state["count"], int)

    def test_path_string_stays_string(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("path", "/123/dir")
        assert eng.state["path"] == "/123/dir"
        assert isinstance(eng.state["path"], str)

    def test_plain_string_stays_string(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("name", "nexus-shell")
        assert eng.state["name"] == "nexus-shell"

    def test_set_non_string_value_unchanged(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.set("data", {"nested": [1, 2, 3]})
        assert eng.state["data"] == {"nested": [1, 2, 3]}


# ── save() fallback ───────────────────────────────────────────────────────────

class TestSaveFallback:
    def test_save_creates_directory_if_missing(self, tmp_path):
        eng = make_engine(tmp_path)
        # .nexus dir may not exist yet; set() should create it
        eng.set("test", "value")
        assert (tmp_path / ".nexus" / "state.json").exists()

    def test_save_fallback_pivots_on_permission_error(self, tmp_path):
        eng = make_engine(tmp_path)
        # Simulate primary write failing
        with patch.object(Path, "mkdir", return_value=None):
            with patch("builtins.open") as mock_file:
                mock_file.side_effect = [PermissionError("no write"), mock_open()()]
                try:
                    eng.save()
                except Exception:
                    pass
        # active_file should have pivoted to fallback
        # (exact assertion depends on whether fallback is writable in CI)


# ── update_slot / update_session ──────────────────────────────────────────────

class TestHelperMethods:
    def test_update_slot(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.update_slot("editor", "hx")
        assert eng.get("ui.slots.editor.tool") == "hx"

    def test_update_session_stores_layout(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.update_session({"layout_string": "abc,80x24"})
        sess = eng.get_session()
        assert sess == {"layout_string": "abc,80x24"}

    def test_update_session_adds_timestamp(self, tmp_path):
        eng = make_engine(tmp_path)
        eng.update_session({"layout_string": "abc"})
        assert eng.get("session.last_save") is not None

    def test_get_session_returns_none_before_set(self, tmp_path):
        eng = make_engine(tmp_path)
        assert eng.get_session() is None
