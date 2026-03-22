"""
Capability launcher handler (Alt+o).

Lists available capabilities and their adapters, and launches
a selected capability with the best (or a specific) adapter.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

from engine.capabilities.base import CapabilityType, AdapterManifest
from engine.capabilities.registry import REGISTRY


# Human-readable labels for each capability type.
_LABELS: Dict[CapabilityType, str] = {
    CapabilityType.EDITOR: "Editor",
    CapabilityType.EXPLORER: "File Explorer",
    CapabilityType.EXECUTOR: "Terminal",
    CapabilityType.AGENT: "AI Agent",
    CapabilityType.CHAT: "Chat",
    CapabilityType.MENU: "Menu",
    CapabilityType.MULTIPLEXER: "Multiplexer",
}

# Map from lowercase type name to CapabilityType enum member.
_TYPE_BY_NAME: Dict[str, CapabilityType] = {
    ct.name: ct for ct in CapabilityType
}


def _adapter_info(adapter, manifest: Optional[AdapterManifest]) -> Dict[str, Any]:
    """Build a JSON-serialisable dict describing an adapter."""
    name = manifest.name if manifest else type(adapter).__name__
    priority = manifest.priority if manifest else 0
    available = adapter.is_available()
    return {"name": name, "priority": priority, "available": available}


def handle_open(registry=None) -> Dict[str, Any]:
    """List all capability types and their registered adapters.

    Parameters
    ----------
    registry:
        Optional override for the global ``REGISTRY`` (useful in tests).
    """
    reg = registry or REGISTRY
    capabilities: List[Dict[str, Any]] = []

    for cap_type in CapabilityType:
        pairs = reg.list_all_with_manifests(cap_type)
        adapters = [_adapter_info(a, m) for a, m in pairs]

        best = reg.get_best(cap_type)
        default_name: Optional[str] = None
        if best is not None:
            default_name = best.manifest.name if best.manifest else type(best).__name__

        capabilities.append({
            "type": cap_type.name,
            "label": _LABELS.get(cap_type, cap_type.name),
            "adapters": adapters,
            "default": default_name,
        })

    return {"action": "show_launcher", "capabilities": capabilities}


def handle_select(
    capability_type: str,
    adapter_name: str = "",
    mode: str = "new_tab",
    registry=None,
) -> Dict[str, Any]:
    """Launch a capability with the best or a specific adapter.

    Parameters
    ----------
    capability_type:
        Name of the ``CapabilityType`` enum member (e.g. ``"EDITOR"``).
    adapter_name:
        If non-empty, selects a specific adapter by name.
    mode:
        ``"new_tab"`` or ``"replace"``.
    registry:
        Optional override for the global ``REGISTRY``.
    """
    reg = registry or REGISTRY
    cap_type = _TYPE_BY_NAME.get(capability_type.upper() if capability_type else "")

    if cap_type is None:
        return {"error": "unknown_capability_type", "capability_type": capability_type}

    # Resolve the adapter
    resolved_name: Optional[str] = None
    if adapter_name:
        # Look for a specific adapter by manifest name
        for adapter, manifest in reg.list_all_with_manifests(cap_type):
            name = manifest.name if manifest else type(adapter).__name__
            if name == adapter_name:
                resolved_name = name
                break
        if resolved_name is None:
            resolved_name = adapter_name  # pass through even if not found
    else:
        best = reg.get_best(cap_type)
        if best is not None:
            resolved_name = best.manifest.name if best.manifest else type(best).__name__

    # Derive a role string for get_launch_command
    role_map = {
        CapabilityType.EDITOR: "editor",
        CapabilityType.EXPLORER: "explorer",
        CapabilityType.EXECUTOR: "terminal",
        CapabilityType.AGENT: "chat",
        CapabilityType.CHAT: "chat",
        CapabilityType.MENU: "menu",
    }
    role = role_map.get(cap_type)
    command = reg.get_launch_command(role) if role else None

    return {
        "action": "launch",
        "capability_type": capability_type,
        "adapter": resolved_name,
        "mode": mode,
        "command": command,
    }
