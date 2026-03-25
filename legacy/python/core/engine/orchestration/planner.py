#!/usr/bin/env python3
# core/engine/orchestration/planner.py
"""
Nexus Workflow Planner (V3)
==========================
Converts Intents into actionable Execution Plans.
"""

import os
from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class OpType(Enum):
    EDIT = auto()     # Open/edit a file in the registered editor
    EXPLORE = auto()  # Open a path in the registered file explorer
    EXECUTE = auto()  # Run a command (exec_local or new pane)
    RENDER = auto()   # Display/render content (markdown, diagrams)
    WAIT = auto()     # Wait for a condition before proceeding
    FOCUS = auto()    # Switch focus to an existing pane/tab
    SPAWN = auto()    # Spawn a new multiplexer pane with a command


@dataclass
class WorkflowStep:
    op: OpType
    capability: str              # e.g. 'Editor', 'Explorer', 'Multiplexer'
    params: Dict[str, Any]
    depends_on: List[int] = field(default_factory=list)   # Indices of prior steps
    strategy: str = "stack_push" # stack_push | stack_switch | stack_replace | exec_local | remote_control


@dataclass
class ExecutionPlan:
    intent: str
    steps: List[WorkflowStep]
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowPlanner:
    """
    Converts a high-level intent dict into an ExecutionPlan.

    Does NOT require runtime context (stack state, bridges).
    For context-aware planning (smart role switching, nvim RPC),
    use IntentResolver.to_plan() which wraps this with live state.
    """

    def plan(self, intent_data: Dict[str, Any]) -> ExecutionPlan:
        """
        Maps a high-level intent to a sequence of capability operations.

        intent_data keys:
            verb    - 'edit' | 'run' | 'view' | 'open'
            type    - ROLE | PLACE | PROJECT | NOTE | DOC | MODEL | AGENT | ACTION
            payload - the target (path, command, role name, etc.)
            intent  - push | replace | swap  (defaults to push)
        """
        verb    = intent_data.get("verb", "run")
        itype   = intent_data.get("type", "ACTION")
        payload = intent_data.get("payload", "")
        intent  = intent_data.get("intent", "push")
        strategy = "stack_replace" if intent == "replace" else "stack_push"

        steps: List[WorkflowStep] = []

        # --- ROLE: Open a named tool role (editor, explorer, chat, terminal…) ---
        if itype == "ROLE":
            role = payload.lower()
            role_defaults = {
                "editor":   os.environ.get("NEXUS_EDITOR", "nvim"),
                "explorer": os.environ.get("NEXUS_EXPLORER", "yazi"),
                "terminal": os.environ.get("SHELL", "zsh"),
                "chat":     "opencode",
            }
            cmd = role_defaults.get(role, role)
            steps.append(WorkflowStep(
                op=OpType.SPAWN,
                capability="Multiplexer",
                params={"command": cmd, "name": role, "role": role},
                strategy=strategy,
            ))

        # --- PLACE / PROJECT: Navigate to a directory ---
        elif itype in ("PLACE", "PROJECT"):
            name = Path(payload).name or payload
            steps.append(WorkflowStep(
                op=OpType.SPAWN,
                capability="Multiplexer",
                params={"command": f"cd {payload!r} && exec ${{SHELL:-zsh}} -i", "name": name},
                strategy=strategy,
            ))

        # --- NOTE / DOC: Open a file in the editor ---
        elif itype in ("NOTE", "DOC"):
            editor_cmd = os.environ.get("NEXUS_EDITOR", "nvim")
            name = Path(payload).name
            steps.append(WorkflowStep(
                op=OpType.EDIT,
                capability="Editor",
                params={"action": "open", "path": payload, "command": f"{editor_cmd} {payload}"},
                strategy=strategy,
            ))

        # --- MODEL / AGENT: Spawn an AI/chat session ---
        elif itype in ("MODEL", "AGENT"):
            nexus_home = os.environ.get("NEXUS_HOME", "")
            if nexus_home:
                cmd = f"{nexus_home}/modules/agents/bin/px-agent chat {payload}"
            else:
                cmd = f"echo 'Agent not configured: {payload}'"
            steps.append(WorkflowStep(
                op=OpType.SPAWN,
                capability="Multiplexer",
                params={"command": cmd, "name": f"Chat: {payload}", "role": "chat"},
                strategy=strategy,
            ))

        # --- ACTION: Run a command or trigger a special system action ---
        elif itype == "ACTION":
            if payload.startswith(":"):
                # Internal system actions run locally (no new pane)
                steps.append(WorkflowStep(
                    op=OpType.EXECUTE,
                    capability="Executor",
                    params={"command": payload},
                    strategy="exec_local",
                ))
            else:
                steps.append(WorkflowStep(
                    op=OpType.EXECUTE,
                    capability="Executor",
                    params={"command": payload},
                    strategy=strategy,
                ))

        # --- Fallback ---
        else:
            steps.append(WorkflowStep(
                op=OpType.EXECUTE,
                capability="Executor",
                params={"command": f"echo 'Unknown intent type: {itype}'"},
                strategy="exec_local",
            ))

        return ExecutionPlan(intent=f"{verb} {itype}", steps=steps)
