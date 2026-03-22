from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


class NodeType(Enum):
    ACTION = "action"
    GROUP = "group"
    LIVE_SOURCE = "live_source"
    SETTING = "setting"


class ActionKind(Enum):
    SHELL = "shell"
    PYTHON = "python"
    INTERNAL = "internal"
    NAVIGATION = "navigation"


class Scope(Enum):
    GLOBAL = "global"
    PROFILE = "profile"
    WORKSPACE = "workspace"


@dataclass
class CommandGraphNode:
    id: str
    label: str
    type: NodeType
    scope: Scope = Scope.GLOBAL
    action_kind: Optional[ActionKind] = None
    command: Optional[str] = None
    children: List['CommandGraphNode'] = field(default_factory=list)
    resolver: Optional[str] = None
    timeout_ms: int = 3000
    cache_ttl_s: int = 30
    config_file: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    icon: Optional[str] = None
    description: Optional[str] = None
    disabled: bool = False
    source_file: Optional[str] = None
