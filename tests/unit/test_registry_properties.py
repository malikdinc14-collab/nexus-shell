#!/usr/bin/env python3
# tests/unit/test_registry_properties.py
import sys
import shutil
import pytest
from pathlib import Path
from hypothesis import given, strategies as st, settings
from unittest.mock import MagicMock, patch

# Path Setup
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "core"))

from engine.capabilities.registry import CapabilityRegistry

@given(st.sampled_from(["editor", "explorer", "chat", "terminal", "viewer", "search"]))
def test_get_tool_for_role_always_returns_valid_tool(role):
    """
    Invariant: get_tool_for_role must always return a string that 
    shutil.which identifies as an executable.
    """
    reg = CapabilityRegistry()
    tool = reg.get_tool_for_role(role)
    assert isinstance(tool, str)
    # Even in a restricted environment, it should return a safe default like 'vim' or 'ls'
    assert shutil.which(tool) is not None

def test_profile_priority_when_available(tmp_path):
    """
    Invariant: If a tool is in the role map and is available, it must be returned.
    """
    @given(
        role=st.sampled_from(["editor", "explorer", "chat"]),
        tool_name=st.text(min_size=1, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    def run_test(role, tool_name):
        import yaml
        mock_profile = tmp_path / "profile.yaml"
        # Clear/Create profile for each run
        with open(mock_profile, 'w') as f:
            yaml.dump({"roles": {role: tool_name}}, f)
        
        reg = CapabilityRegistry(profile_path=mock_profile)
        
        with patch("shutil.which", return_value=f"/bin/{tool_name}"):
            resolved = reg.get_tool_for_role(role)
            assert resolved == f"/bin/{tool_name}"
    
    run_test()

@given(st.sampled_from(["editor", "explorer", "chat"]))
def test_fallback_logic_traversal(role):
    """
    Invariant: If primary choice is missing, it must traverse tiers.
    """
    reg = CapabilityRegistry()
    
    # Mocking shutil.which to fail for the first few options
    fallbacks = {
        "editor": ["nvim", "vim", "vi", "nano", "micro"],
        "explorer": ["yazi", "ranger", "mc", "ls"],
        "chat": ["opencode", "aider", "bash"],
    }
    
    options = fallbacks[role]
    if len(options) < 2:
        return

    # Target the second option
    target_tool = options[1]
    
    def mock_which(cmd):
        if cmd == target_tool:
            return f"/usr/bin/{target_tool}"
        return None

    with patch("shutil.which", side_effect=mock_which):
        resolved = reg.get_tool_for_role(role)
        assert resolved == f"/usr/bin/{target_tool}"

def test_get_launch_command_preserves_custom_json():
    """
    Invariant: If no adapter exists, preserve the custom command (Fixed Bug).
    """
    reg = CapabilityRegistry()
    # 'server' is not a standard role with an adapter
    cmd = reg.get_launch_command("server")
    assert cmd is None # This tells the orchestrator to use the JSON command
