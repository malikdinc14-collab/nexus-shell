#!/usr/bin/env python3
# core/engine/capabilities/registry.py
"""
Nexus Capability Registry (V3)
==============================
Manages the lifecycle and discovery of capabilities and their adapters.
"""

from typing import Dict, List, Optional, Tuple, Type
from pathlib import Path
from .base import Capability, CapabilityType, AdapterManifest
from .adapters.agent.opencode import OpenCodeAdapter
from .adapters.explorer.yazi import YaziAdapter
from .adapters.editor.neovim import NeovimAdapter
from .adapters.menu.gum_menu import GumMenuAdapter
from .adapters.menu.textual_menu import TextualMenuAdapter
from .adapters.menu.fzf_menu import FzfMenuAdapter
from .adapters.menu.null_menu import NullMenuAdapter

class CapabilityRegistry:
    """Central registry for discovering which tool implements which capability."""
    
    def __init__(self, profile_path: Optional[Path] = None):
        self._capabilities: Dict[CapabilityType, List[Capability]] = {
            t: [] for t in CapabilityType
        }
        self._profile_path = profile_path
        self._role_map = self._load_role_map()
        self._auto_register()

    def _auto_register(self):
        """Auto-register known adapters.

        NullMenuAdapter is always registered last as the lowest-priority
        fallback for MENU capability. It guarantees that get_best(MENU)
        never returns None.
        """
        adapters = [
            OpenCodeAdapter(),
            YaziAdapter(),
            NeovimAdapter(),
            TextualMenuAdapter(),
            FzfMenuAdapter(),
            GumMenuAdapter(),
        ]
        for a in adapters:
            if a.is_available():
                self.register(a)

        # Always register NullMenuAdapter as last-resort fallback
        self.register(NullMenuAdapter())

    def _load_role_map(self) -> Dict[str, str]:
        """Loads the role-to-tool mapping from the user's profile.
        
        Invariant: The returned map only contains roles whose tools are
        currently available in the system PATH. Stale profile entries
        (tools installed at profile-write time but since removed, or
        tools not yet installed) are silently dropped so downstream
        tiered fallbacks can take over.
        """
        if not self._profile_path or not self._profile_path.exists():
            return {}
        try:
            import yaml
            import shutil
            with open(self._profile_path) as f:
                data = yaml.safe_load(f) or {}
            raw_roles = data.get("roles", {})
            # Re-validate: only keep roles whose tool actually exists right now
            return {
                role: tool
                for role, tool in raw_roles.items()
                if shutil.which(tool)
            }
        except:
            return {}

    def _find_first_available(self, tools: List[str]) -> Optional[str]:
        """Returns the first tool in the list that exists in the system PATH."""
        import shutil
        for tool in tools:
            path = shutil.which(tool)
            if path:
                return path
        return None

    def get_tool_for_role(self, role: str) -> str:
        """The Python-equivalent of the legacy Bash get_tool_for_role."""
        # 1. Check Profile Map (Verify availability)
        import shutil
        if role in self._role_map:
            tool = self._role_map[role]
            # If the tool is an absolute path or in PATH, use it.
            path = shutil.which(tool)
            if path:
                return path
            # Otherwise, log warning and fall through to tiers
        
        # 2. Tiered Fallbacks with Discovery
        fallbacks = {
            "editor": ["nvim", "vim", "vi", "nano", "micro"],
            "explorer": ["yazi", "ranger", "mc", "ls"],
            "chat": ["opencode", "aider", "bash"],
            "terminal": ["zsh", "bash", "sh"],
            "viewer": ["glow", "bat", "cat"],
            "search": ["rg", "grep"]
        }
        
        options = fallbacks.get(role, [])
        found = self._find_first_available(options)
        if found:
            return found
            
        # 3. Absolute Last Resort
        defaults = {
            "editor": "/usr/bin/vim",
            "explorer": "/bin/ls",
            "chat": "/bin/bash",
            "terminal": "/usr/bin/zsh",
            "viewer": "/bin/cat",
            "search": "/usr/bin/grep"
        }
        return defaults.get(role, "echo")

    def get_launch_command(self, role: str) -> str:
        """
        Returns the best launch command for a role, using the adapter's
        get_launch_command() if available, otherwise falling back to
        the raw tool name.
        """
        cap_type_map = {
            "chat": CapabilityType.CHAT,
            "editor": CapabilityType.EDITOR,
            "explorer": CapabilityType.EXPLORER,
            "menu": CapabilityType.MENU,
        }
        cap_type = cap_type_map.get(role)
        if cap_type:
            best = self.get_best(cap_type)
            if best and hasattr(best, "get_launch_command"):
                return best.get_launch_command()
        
        # Invariant: If there is no specific capability adapter with specialized
        # socket logic, we defer to the raw command defined in the layout JSON.
        # Returning a generic fallback tool here (like 'echo' or 'zsh') would
        # silently destroy custom commands like 'npm run dev' or 'htop'.
        return None

    def register(self, capability: Capability):
        """Registers an adapter instance for a specific capability."""
        self._capabilities[capability.capability_type].append(capability)

    def get_best(self, cap_type: CapabilityType) -> Optional[Capability]:
        """Returns the highest-priority available capability provider.

        When adapters declare a manifest, they are sorted by
        manifest.priority (highest first). Adapters without a manifest
        are treated as priority 0 and appear after all manifested ones.
        """
        available = [c for c in self._capabilities[cap_type] if c.is_available()]
        if not available:
            return None
        available.sort(
            key=lambda c: c.manifest.priority if c.manifest else 0,
            reverse=True,
        )
        return available[0]

    def list_all(self, cap_type: CapabilityType) -> List[Capability]:
        """Lists all registered providers for a type."""
        return self._capabilities.get(cap_type, [])

    def list_all_with_manifests(
        self, cap_type: CapabilityType
    ) -> List[Tuple[Capability, Optional[AdapterManifest]]]:
        """Returns all registered adapters for a type paired with their manifest."""
        return [
            (c, c.manifest) for c in self._capabilities.get(cap_type, [])
        ]

# Global Registry Instance
REGISTRY = CapabilityRegistry()
