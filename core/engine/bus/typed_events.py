"""Typed event definitions for the Nexus event bus."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class EventType(Enum):
    """All known event types in the Nexus event bus."""

    STACK_PUSH = "stack.push"
    STACK_POP = "stack.pop"
    STACK_ROTATE = "stack.rotate"
    PANE_SPLIT = "pane.split"
    PANE_KILL = "pane.kill"
    TAB_SWITCH = "tab.switch"
    PROFILE_SWITCH = "profile.switch"
    PACK_ENABLE = "pack.enable"
    PACK_DISABLE = "pack.disable"
    CONFIG_RELOAD = "config.reload"
    COMPOSITION_SWITCH = "composition.switch"
    WORKSPACE_SAVE = "workspace.save"
    WORKSPACE_RESTORE = "workspace.restore"
    CUSTOM = "custom"


@dataclass
class TypedEvent:
    """A structured event with type, source, payload, and timestamp."""

    event_type: EventType
    source: str
    payload: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


def create_event(event_type: EventType, source: str, **kwargs) -> TypedEvent:
    """Convenience function to create a TypedEvent with keyword payload."""
    return TypedEvent(event_type=event_type, source=source, payload=kwargs)
