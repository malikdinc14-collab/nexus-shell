#!/usr/bin/env python3
# core/engine/capabilities/registry.py
"""
Nexus Capability Registry (V3)
==============================
Manages the lifecycle and discovery of capabilities and their adapters.
"""

from typing import Dict, List, Optional, Type
from pathlib import Path
from .base import Capability, CapabilityType

class CapabilityRegistry:
    """Central registry for discovering which tool implements which capability."""
    
    def __init__(self, profile_path: Optional[Path] = None):
        self._capabilities: Dict[CapabilityType, List[Capability]] = {
            t: [] for t in CapabilityType
        }
        self._profile_path = profile_path
        self._role_map = self._load_role_map()

    def _load_role_map(self) -> Dict[str, str]:
        """Loads the role-to-tool mapping from the user's profile."""
        if not self._profile_path or not self._profile_path.exists():
            return {}
        try:
            import yaml
            with open(self._profile_path) as f:
                data = yaml.safe_load(f) or {}
                return data.get("roles", {})
        except:
            return {}

    def get_tool_for_role(self, role: str) -> str:
        """The Python-equivalent of the legacy Bash get_tool_for_role."""
        # 1. Check Profile Map
        if role in self._role_map:
            return self._role_map[role]
        
        # 2. Fallbacks
        fallbacks = {
            "editor": "nvim",
            "explorer": "yazi",
            "chat": "opencode",
            "terminal": "zsh",
            "viewer": "cat",
            "search": "rg"
        }
        return fallbacks.get(role, "echo")

    def register(self, capability: Capability):
        """Registers an adapter instance for a specific capability."""
        self._capabilities[capability.capability_type].append(capability)

    def get_best(self, cap_type: CapabilityType) -> Optional[Capability]:
        """Returns the most appropriate available capability provider."""
        available = [c for c in self._capabilities[cap_type] if c.is_available()]
        return available[0] if available else None

    def list_all(self, cap_type: CapabilityType) -> List[Capability]:
        """Lists all registered providers for a type."""
        return self._capabilities.get(cap_type, [])

# Global Registry Instance
REGISTRY = CapabilityRegistry()
