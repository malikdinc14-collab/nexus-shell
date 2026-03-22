"""
NexusCore — the single entry point for all Nexus Shell operations.

The core is surface-agnostic. Inject a Surface implementation at
construction time. All state lives here; the surface is a dumb renderer.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.surfaces import Surface, MenuItem, HudModule, ContainerInfo
from engine.stacks.manager import StackManager
from engine.stacks.stack import Tab
from engine.bus.enhanced_bus import EnhancedBus
from engine.bus.typed_events import create_event, EventType
from engine.config.cascade import CascadeResolver
from engine.graph.node import CommandGraphNode
from engine.graph.loader import load_nodes_from_yaml
from engine.graph.resolver import resolve_tree
from engine.graph.live_sources import get_registry, resolve_all_live_sources
from engine.momentum.session import save_session, restore_session, load_geometry
from engine.api.menu_handler import build_menu_items

logger = logging.getLogger(__name__)


class NexusCore:
    """Facade wrapping all engine modules behind a surface-agnostic API."""

    def __init__(
        self,
        surface: Surface,
        config_dir: Optional[str] = None,
        workspace_dir: Optional[str] = None,
    ):
        self.surface = surface
        self.stacks = StackManager()
        self.bus = EnhancedBus()
        self.live_sources = get_registry()

        # Config
        self._config_dir = config_dir or os.path.expanduser("~/.config/nexus")
        self._workspace_dir = workspace_dir or os.path.join(os.getcwd(), ".nexus")
        self.config = CascadeResolver(
            global_dir=Path(self._config_dir),
            workspace_dir=Path(self._workspace_dir),
        )

        self._session: Optional[str] = None
        self._menu_yaml: Optional[str] = None

    # -- Workspace -------------------------------------------------------------

    def create_workspace(self, name: str, cwd: str = "") -> str:
        """Initialize a workspace session on the surface."""
        self._session = self.surface.initialize(name, cwd=cwd or os.getcwd())
        self.bus.publish(create_event(
            EventType.CUSTOM, "workspace.created", name=name,
        ))
        logger.info("Workspace created: %s", name)
        return self._session

    def save_workspace(self, session_dir: str) -> None:
        """Persist workspace state (stacks + geometry)."""
        try:
            save_session(self.stacks, session_dir)
            logger.info("Workspace saved to %s", session_dir)
        except Exception:
            logger.exception("Failed to save workspace")
            raise

    def restore_workspace(self, session_dir: str):
        """Restore workspace state from disk."""
        try:
            deferred = restore_session(self.stacks, session_dir)
            geometry = load_geometry(session_dir)
            logger.info(
                "Workspace restored from %s (%d deferred)",
                session_dir, deferred.pending_count(),
            )
            return deferred, geometry
        except Exception:
            logger.exception("Failed to restore workspace")
            raise

    # -- Tab Stacks ------------------------------------------------------------

    def push_tab(self, pane_id: str, capability_type: str = "terminal",
                 adapter_name: str = "") -> Optional[Tab]:
        """Push a new tab onto a pane's stack."""
        tab = Tab(
            id=f"{pane_id}:{len(self.stacks.get_or_create(pane_id).tabs)}",
            capability_type=capability_type,
            adapter_name=adapter_name,
        )
        result = self.stacks.push(pane_id, tab)
        if result is None:  # Success (no sentinel returned)
            self.bus.publish(create_event(
                EventType.STACK_PUSH, "tab.pushed", pane=pane_id, tab=tab.id,
            ))
            return tab
        return None

    def pop_tab(self, pane_id: str) -> Optional[Tab]:
        """Pop the active tab from a pane's stack."""
        result = self.stacks.pop(pane_id)
        if hasattr(result, "id"):
            self.bus.publish(create_event(
                EventType.STACK_POP, "tab.popped", pane=pane_id, tab=result.id,
            ))
            return result
        return None

    def rotate_tabs(self, pane_id: str, direction: int = 1) -> Optional[Tab]:
        """Rotate through tabs in a pane's stack."""
        result = self.stacks.rotate(pane_id, direction)
        if result and hasattr(result, "id"):
            self.bus.publish(create_event(
                EventType.STACK_ROTATE, "tab.rotated",
                pane=pane_id, tab=result.id,
            ))
            return result
        return None

    def list_tabs(self, pane_id: str) -> List[dict]:
        """List tabs in a pane's stack."""
        stack = self.stacks.get_stack(pane_id)
        if stack is None:
            return []
        return [
            {
                "id": t.id,
                "capability_type": t.capability_type,
                "adapter_name": t.adapter_name,
                "active": t is stack.active_tab,
            }
            for t in stack.tabs
        ]

    # -- Command Graph / Menu --------------------------------------------------

    def open_menu(self, yaml_path: Optional[str] = None) -> List[dict]:
        """Load and return menu items with live source values resolved."""
        path = yaml_path or self._menu_yaml
        if not path:
            return []
        nodes = load_nodes_from_yaml(path)
        items = build_menu_items(nodes)

        # Resolve live sources
        live_nodes = [
            {"node_id": item["id"], "resolver": item["resolver"]}
            for item in items if "resolver" in item
        ]
        if live_nodes:
            import asyncio
            try:
                resolved = asyncio.run(resolve_all_live_sources(live_nodes))
                for item in items:
                    if item["id"] in resolved:
                        item["value"] = resolved[item["id"]]
            except Exception:
                logger.warning("Live source resolution failed", exc_info=True)

        return items

    def set_menu_yaml(self, path: str) -> None:
        """Set the path to the system root menu YAML."""
        self._menu_yaml = path

    # -- Packs & Profiles ------------------------------------------------------

    def suggest_packs(self, directory: str,
                      pack_dirs: Optional[List[str]] = None) -> List[dict]:
        """Detect and suggest packs for a directory."""
        from engine.packs.manager import PackManager
        mgr = PackManager(pack_dirs or [])
        suggestions = mgr.suggest(directory)
        return [{"name": p.name, "markers": p.markers} for p in suggestions]

    def switch_profile(self, name: str, profiles_dir: str = "") -> bool:
        """Switch the active profile."""
        from engine.profiles.manager import ProfileManager
        mgr = ProfileManager(profiles_dir)
        return mgr.switch(name)

    # -- Event Bus -------------------------------------------------------------

    def publish(self, source: str, data: Optional[dict] = None, **kwargs) -> None:
        """Publish an event to the bus."""
        payload = dict(data or {})
        payload.update(kwargs)
        self.bus.publish(create_event(EventType.CUSTOM, source, **payload))

    def subscribe(self, pattern: str, callback) -> None:
        """Subscribe to events matching a pattern."""
        self.bus.subscribe(pattern, callback)

    # -- Config ----------------------------------------------------------------

    def get_config(self, filename: str, key: str = "") -> Any:
        """Get a config value through the cascade resolver."""
        return self.config.get(filename, key) if key else self.config.get(filename)

    def reload_config(self) -> None:
        """Reload config from disk."""
        self.config = CascadeResolver(
            global_dir=Path(self._config_dir),
            workspace_dir=Path(self._workspace_dir),
        )
        logger.info("Config reloaded")
