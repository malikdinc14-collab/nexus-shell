from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class HudModuleDef:
    """Definition of a HUD status module provided by a pack."""
    id: str
    label: str
    resolver: str = ""  # Live source resolver name
    position: str = "right"
    color: Optional[str] = None


@dataclass
class ConnectorDef:
    """Event-to-action automation rule."""
    name: str = ""
    trigger: str = ""   # Event pattern, e.g. "editor.save:*.py"
    action: str = ""    # Shell command or internal action


@dataclass
class CommandDef:
    """A command graph node contributed by a pack."""
    id: str
    label: str
    command: str = ""
    icon: Optional[str] = None
    description: Optional[str] = None


@dataclass
class CapabilitySpec:
    """Preferred capability/adapter mapping for a pack."""
    capability_type: str  # "editor", "explorer", etc.
    adapter: str = ""     # Preferred adapter name
    required: bool = False


@dataclass
class Pack:
    """A domain capability bundle."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    markers: List[str] = field(default_factory=list)

    # Tools (existing)
    tools: Dict[str, str] = field(default_factory=dict)

    # Domain configuration
    capabilities: List[CapabilitySpec] = field(default_factory=list)
    compositions: List[str] = field(default_factory=list)
    hud_modules: List[HudModuleDef] = field(default_factory=list)
    commands: List[CommandDef] = field(default_factory=list)
    connectors: List[ConnectorDef] = field(default_factory=list)
    keybinds: Dict[str, str] = field(default_factory=dict)

    # Environment
    env_vars: Dict[str, str] = field(default_factory=dict)
    setup_hook: Optional[str] = None
    teardown_hook: Optional[str] = None

    # Legacy fields (kept for backward compat with existing YAML)
    services: List[Dict[str, Any]] = field(default_factory=list)
    menu_nodes: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)

    # Runtime state
    enabled: bool = False


def load_pack_from_yaml(path: str) -> Optional[Pack]:
    """Load a Pack from a YAML file. Returns None on error."""
    import logging
    import yaml

    logger = logging.getLogger(__name__)
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Parse nested dataclass lists gracefully
        capabilities = [
            CapabilitySpec(**c) for c in data.get("capabilities", [])
            if isinstance(c, dict)
        ]
        hud_modules = [
            HudModuleDef(**h) for h in data.get("hud_modules", [])
            if isinstance(h, dict)
        ]
        commands = [
            CommandDef(**c) for c in data.get("commands", [])
            if isinstance(c, dict)
        ]
        connectors_raw = data.get("connectors", [])
        connectors = []
        for c in connectors_raw:
            if isinstance(c, dict) and ("trigger" in c or "action" in c):
                connectors.append(ConnectorDef(**{
                    k: v for k, v in c.items()
                    if k in ("name", "trigger", "action")
                }))

        return Pack(
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            markers=data.get("markers", []),
            tools=data.get("tools", {}),
            capabilities=capabilities,
            compositions=data.get("compositions", []),
            hud_modules=hud_modules,
            commands=commands,
            connectors=connectors,
            keybinds=data.get("keybinds", {}),
            env_vars=data.get("env_vars", {}),
            setup_hook=data.get("setup_hook"),
            teardown_hook=data.get("teardown_hook"),
            services=data.get("services", []),
            menu_nodes=data.get("menu_nodes", []),
            actions=data.get("actions", []),
            enabled=data.get("enabled", False),
        )
    except Exception:
        logger.warning("Failed to load pack from %s", path, exc_info=True)
        return None
