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
from engine.project.discovery import ProjectConfig, discover
from engine.project.boot import BootRunner, BootResult
from engine.project.menu import load_project_menu

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
        self._project: Optional[ProjectConfig] = None
        self._boot_runner: Optional[BootRunner] = None

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

    # -- Project ---------------------------------------------------------------

    def discover_project(self, project_root: str = "") -> Optional[ProjectConfig]:
        """Discover and load `.nexus/` config for a project directory.

        If found, stores the config and emits a `project.discovered` event.
        Automatically updates the cascade resolver with the project's workspace dir.
        """
        root = project_root or os.getcwd()
        config = discover(root)
        if config is None:
            logger.debug("No .nexus/ found in %s", root)
            return None

        self._project = config

        # Update cascade resolver to use the project's .nexus/ as workspace layer
        self.config = CascadeResolver(
            global_dir=Path(self._config_dir),
            workspace_dir=config.nexus_dir,
            profile=config.profile,
        )

        self.bus.publish(create_event(
            EventType.PROJECT_DISCOVERED, "project.discovered",
            root=str(config.root),
            profile=config.profile,
            theme=config.theme,
            composition=config.composition,
            boot_count=len(config.boot_items),
            has_menu=config.menu_path is not None,
        ))

        logger.info(
            "Project discovered: %s (boot=%d, menu=%s, profile=%s)",
            config.root.name, len(config.boot_items),
            bool(config.menu_path), config.profile,
        )
        return config

    def run_boot(self, env_override: Optional[Dict[str, str]] = None) -> Optional[BootResult]:
        """Execute the project's boot list if one was discovered.

        Returns BootResult or None if no project/boot items.
        """
        if not self._project or not self._project.boot_items:
            return None

        def _on_progress(current: int, total: int, label: str):
            self.bus.publish(create_event(
                EventType.BOOT_PROGRESS, "boot.progress",
                current=current, total=total, label=label,
            ))

        self._boot_runner = BootRunner(on_progress=_on_progress)

        self.bus.publish(create_event(
            EventType.BOOT_START, "boot.start",
            total=len(self._project.boot_items),
        ))

        result = self._boot_runner.run(
            self._project.boot_items,
            cwd=str(self._project.root),
            env_override=env_override,
        )

        self.bus.publish(create_event(
            EventType.BOOT_COMPLETE, "boot.complete",
            total=result.total,
            completed=result.completed,
            failed=result.failed,
            background=result.background,
            success=result.success,
        ))

        return result

    def shutdown_boot(self) -> int:
        """Kill all background processes started by the boot runner."""
        if not self._boot_runner:
            return 0
        count = self._boot_runner.shutdown()
        if count:
            self.bus.publish(create_event(
                EventType.BOOT_SHUTDOWN, "boot.shutdown", killed=count,
            ))
            logger.info("Shut down %d boot processes", count)
        return count

    def get_project_menu_nodes(self) -> List[CommandGraphNode]:
        """Load project menu nodes from `.nexus/menu.yaml` if discovered."""
        if not self._project or not self._project.menu_path:
            return []
        return load_project_menu(self._project.menu_path)

    @property
    def project(self) -> Optional[ProjectConfig]:
        """The currently loaded project config, or None."""
        return self._project

    # -- Tab Stacks ------------------------------------------------------------

    def handle_stack_op(self, op: str, payload: dict) -> Dict:
        """Route a stack operation through NexusCore.

        This is the single entry point for all stack mutations. The daemon
        calls this instead of managing state directly.

        Operations: push, switch, replace, close, adopt, list
        """
        ops = {
            "push": self._stack_push,
            "switch": self._stack_switch,
            "replace": self._stack_replace,
            "close": self._stack_close,
            "adopt": self._stack_adopt,
            "tag": self._stack_tag,
            "untag": self._stack_untag,
            "rename": self._stack_rename,
        }
        handler = ops.get(op)
        if handler is None:
            return {"status": "error", "error": "unknown_op", "op": op}
        return handler(payload)

    def _get_visible_container(self, stack, focused_id: str) -> Optional[str]:
        """Find the actually-visible pane in a stack.

        Matches daemon's defensive lookup: checks focused_id membership,
        then status, then falls back to active_index.
        """
        if not stack.tabs:
            return None
        # If focused pane is in this stack, it's the visible one
        for tab in stack.tabs:
            if tab.tmux_pane_id == focused_id:
                return focused_id
        # Find by VISIBLE status
        for tab in stack.tabs:
            if tab.status == "VISIBLE":
                return tab.tmux_pane_id
        # Fallback: whatever active_index says
        active = stack.active_tab
        return active.tmux_pane_id if active else None

    def _stack_push(self, payload: dict) -> Dict:
        """Push a new pane onto a stack, ghost-swapping the visible pane out."""
        identity = payload.get("identity", "")
        new_pane_id = payload.get("pane_id")
        name = payload.get("name", "Shell")
        focused_id = payload.get("focused_id") or self.surface.get_focused(self._session)

        if not new_pane_id:
            return {"status": "error", "error": "no_pane_id"}

        sid, stack = self.stacks.get_or_create_by_identity(identity, initial_pane=focused_id)

        # Tag the pane with stack identity
        if identity and not identity.startswith("stack_") and not stack.role:
            stack.role = identity
            if focused_id:
                self.surface.set_tag(focused_id, "nexus_role", identity)

        visible_id = self._get_visible_container(stack, focused_id)

        # Record geometry of outgoing pane, mark all existing tabs as background
        if visible_id:
            geo = self.surface.get_geometry(visible_id)
            for tab in stack.tabs:
                tab.status = "BACKGROUND"
                tab.is_active = False
                if tab.tmux_pane_id == visible_id:
                    tab.geometry = geo

        # Ghost-swap: move visible pane to reservoir, new pane takes its place
        if visible_id and not self.surface.swap_containers(visible_id, new_pane_id):
            logger.error(
                "[INVARIANT] stack push ghost_swap failed: %s -> %s",
                visible_id, new_pane_id,
            )
            return {"status": "error", "error": "swap_failed",
                    "source": visible_id, "target": new_pane_id}

        self.surface.focus(new_pane_id)

        # Add the new tab
        new_tab = Tab(
            tmux_pane_id=new_pane_id,
            name=name,
            status="VISIBLE",
            is_active=True,
            geometry=self.surface.get_geometry(new_pane_id) if visible_id else None,
        )
        stack.tabs.append(new_tab)
        stack.active_index = len(stack.tabs) - 1

        # Tag the pane
        self.surface.set_tag(new_pane_id, "nexus_stack_id", sid)

        self.bus.publish(create_event(
            EventType.STACK_PUSH, "stack.push",
            stack_id=sid, pane=new_pane_id, name=name,
        ))
        logger.info("Stack push: %s -> %s (stack=%s)", visible_id, new_pane_id, sid)
        return {"status": "ok", "stack_id": sid}

    def _stack_switch(self, payload: dict) -> Dict:
        """Switch to a specific tab index within a stack."""
        identity = payload.get("identity", "")
        try:
            index = int(payload.get("index", 0))
        except (TypeError, ValueError):
            return {"status": "error", "error": "invalid_index"}

        sid, stack = self.stacks.get_by_identity(identity)
        if not stack or index >= len(stack.tabs):
            return {"status": "error", "error": "not_found"}

        target_tab = stack.tabs[index]
        target_id = target_tab.tmux_pane_id
        focused_id = payload.get("focused_id") or self.surface.get_focused(self._session)
        visible_id = self._get_visible_container(stack, focused_id)

        if visible_id == target_id:
            return {"status": "ok", "message": "already_active"}

        # Snapshot outgoing geometry
        outgoing_geo = self.surface.get_geometry(visible_id) if visible_id else None

        if not self.surface.swap_containers(visible_id, target_id):
            return {"status": "error", "error": "swap_failed"}

        self.surface.focus(target_id)

        # Restore incoming geometry if available
        if target_tab.geometry:
            self.surface.set_geometry(target_id, target_tab.geometry)

        # Update status for all tabs
        for i, tab in enumerate(stack.tabs):
            if tab.tmux_pane_id == visible_id:
                tab.geometry = outgoing_geo
            tab.status = "VISIBLE" if i == index else "BACKGROUND"
            tab.is_active = (i == index)

        stack.active_index = index

        self.bus.publish(create_event(
            EventType.STACK_SWITCH, "stack.switch",
            stack_id=sid, pane=target_id, index=index,
        ))
        return {"status": "ok"}

    def _stack_replace(self, payload: dict) -> Dict:
        """Replace the active tab with a new pane."""
        identity = payload.get("identity", "")
        new_pane_id = payload.get("pane_id")
        name = payload.get("name", "Shell")

        sid, stack = self.stacks.get_by_identity(identity)
        if not stack:
            return self._stack_push(payload)

        idx = stack.active_index
        old_tab = stack.tabs[idx]
        old_pane_id = old_tab.tmux_pane_id
        focused_id = payload.get("focused_id") or self.surface.get_focused(self._session)
        visible_id = self._get_visible_container(stack, focused_id)

        geo = self.surface.get_geometry(visible_id) if visible_id else None

        if not self.surface.swap_containers(visible_id, new_pane_id):
            return {"status": "error", "error": "swap_failed"}

        self.surface.focus(new_pane_id)
        if geo:
            self.surface.set_geometry(new_pane_id, geo)

        # Kill old pane if different from new
        if old_pane_id and old_pane_id != new_pane_id:
            self.surface.destroy_container(old_pane_id)

        # Replace the tab in-place
        stack.tabs[idx] = Tab(
            tmux_pane_id=new_pane_id,
            name=name,
            status="VISIBLE",
            is_active=True,
            geometry=geo,
        )

        self.bus.publish(create_event(
            EventType.STACK_REPLACE, "stack.replace",
            stack_id=sid, old_pane=old_pane_id, new_pane=new_pane_id,
        ))
        return {"status": "ok"}

    def _stack_close(self, payload: dict) -> Dict:
        """Close the active tab and swap back to the foundation (index 0)."""
        identity = payload.get("identity", "")

        sid, stack = self.stacks.get_by_identity(identity)
        if not stack or not stack.tabs:
            return {"status": "error", "error": "empty"}

        idx = stack.active_index
        if idx == 0:
            return {"status": "error", "error": "foundation_protected"}

        target_tab = stack.tabs[idx]
        target_id = target_tab.tmux_pane_id
        focused_id = payload.get("focused_id") or self.surface.get_focused(self._session)
        visible_id = self._get_visible_container(stack, focused_id)
        foundation_id = stack.tabs[0].tmux_pane_id

        if not self.surface.swap_containers(visible_id, foundation_id):
            return {"status": "error", "error": "swap_failed"}

        self.surface.focus(foundation_id)

        # Kill the closed pane
        if target_id:
            self.surface.destroy_container(target_id)

        stack.tabs.pop(idx)
        stack.active_index = 0
        for i, tab in enumerate(stack.tabs):
            tab.status = "VISIBLE" if i == 0 else "BACKGROUND"
            tab.is_active = (i == 0)

        self.bus.publish(create_event(
            EventType.STACK_CLOSE, "stack.close",
            stack_id=sid, closed_pane=target_id,
        ))
        return {"status": "ok"}

    def _stack_adopt(self, payload: dict) -> Dict:
        """Adopt a pre-existing pane into the stack registry without swapping."""
        identity = payload.get("identity", "")
        pane_id = payload.get("pane_id")
        name = payload.get("name", "Shell")

        if not pane_id:
            return {"status": "error", "error": "no_pane_id"}

        sid, stack = self.stacks.get_or_create_by_identity(identity, initial_pane=pane_id)

        # Mark the pane as visible in the stack
        for tab in stack.tabs:
            if tab.tmux_pane_id == pane_id:
                tab.status = "VISIBLE"
                tab.name = name

        # Tag pane with identity
        self.surface.set_tag(pane_id, "nexus_stack_id", sid)
        if stack.role:
            self.surface.set_tag(pane_id, "nexus_role", stack.role)

        return {"status": "ok", "stack_id": sid}

    def _stack_tag(self, payload: dict) -> Dict:
        """Add a tag to a stack."""
        identity = payload.get("identity", "")
        tag = payload.get("tag")
        if not tag:
            return {"status": "error", "error": "no_tag"}

        sid, stack = self.stacks.get_by_identity(identity)
        if not stack:
            return {"status": "error", "error": "not_found"}

        if tag not in stack.tags:
            stack.tags.append(tag)
        return {"status": "ok", "stack_id": sid}

    def _stack_untag(self, payload: dict) -> Dict:
        """Remove a tag from a stack."""
        identity = payload.get("identity", "")
        tag = payload.get("tag")

        sid, stack = self.stacks.get_by_identity(identity)
        if not stack:
            return {"status": "error", "error": "not_found"}

        if tag and tag in stack.tags:
            stack.tags.remove(tag)
        return {"status": "ok", "stack_id": sid}

    def _stack_rename(self, payload: dict) -> Dict:
        """Rename a stack's role."""
        identity = payload.get("identity", "")
        name = payload.get("name")
        if not name:
            return {"status": "error", "error": "no_name"}

        sid, stack = self.stacks.get_by_identity(identity)
        if not stack:
            return {"status": "error", "error": "not_found"}

        stack.role = name
        return {"status": "ok", "stack_id": sid}

    def list_tabs(self, identity: str) -> List[dict]:
        """List tabs in a stack by identity."""
        sid, stack = self.stacks.get_by_identity(identity)
        if not stack:
            return []
        return [
            {
                "id": t.tmux_pane_id or t.id,
                "name": t.name,
                "status": t.status,
                "active": t.is_active,
                "geometry": t.geometry,
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

    def select_and_dispatch(
        self, node_id: str, mode: str = "new_tab", session: Optional[str] = None
    ) -> Dict:
        """Resolve a menu node by ID and dispatch its action through the surface.

        This is the complete select→dispatch flow: load the full cascade,
        find the node, and execute the command. Returns a status dict.
        """
        from engine.api.menu_handler import load_cascade, _build_node_index

        nodes = load_cascade()
        index = _build_node_index(nodes)
        node = index.get(node_id)

        if node is None:
            logger.error(
                "[INVARIANT] Node '%s' not found in cascade — "
                "open/select see different nodes", node_id,
            )
            return {"status": "error", "error": "node_not_found", "node_id": node_id}

        from engine.graph.node import NodeType

        if node.type == NodeType.SETTING and node.config_file:
            return {
                "status": "ok",
                "action": "edit",
                "node_id": node_id,
                "config_file": node.config_file,
            }

        if not node.command:
            return {
                "status": "error",
                "error": "no_command",
                "node_id": node_id,
                "node_type": node.type.value,
            }

        # Dispatch through the surface — the command runs in the focused pane
        target = session or self._session
        focused = self.surface.get_focused(target) if target else None

        if focused:
            self.surface.send_input(focused, node.command + "\n")
        else:
            # Fallback: send to whatever tmux considers the active pane
            self.surface.send_input("", node.command + "\n")

        self.bus.publish(create_event(
            EventType.CUSTOM, "menu.action.dispatched",
            node_id=node_id, command=node.command, mode=mode,
        ))

        logger.info("Dispatched menu action: %s → %s", node_id, node.command)
        return {
            "status": "ok",
            "action": "dispatched",
            "node_id": node_id,
            "command": node.command,
        }

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
