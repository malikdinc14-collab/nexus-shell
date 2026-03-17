#!/usr/bin/env python3
# core/api/intent_resolver.py
# --- Nexus Intelligence Kernel ---
# Consolidates logic from router.sh and nxs-action-dispatch.
# Resolves (Verb, Type, Payload) -> Execution Plan.

import os
import sys
import json
import subprocess
from pathlib import Path

# Add core/api to path for module imports
sys.path.append(str(Path(__file__).resolve().parent))
try:
    from module_registry import resolve_role
    from control_bridge import ControlBridge
except ImportError:
    def resolve_role(r): return f"echo 'No registry: {r}'"
    class ControlBridge: 
        def get_nvim_pipe(self): return None
        def send_to_role(self, r, c): return False, "N/A"

def log(msg):
    log_file = Path(f"/tmp/nexus_{os.getlogin()}/kernel.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(f"[Kernel] {msg}\n")

class IntentResolver:
    def __init__(self):
        self.nexus_home = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[2]))
        self.stack_bin = self.nexus_home / "core/stack/nxs-stack"
        self.bridge = ControlBridge()

    def get_stack_state(self, role="local"):
        """Queries the stack manager for the current state of a role."""
        try:
            res = subprocess.check_output([str(self.stack_bin), "list", role], stderr=subprocess.DEVNULL)
            return json.loads(res.decode())
        except:
            return {}

    def resolve(self, verb, item_type, payload, intent="push", caller="terminal"):
        """
        The Master Resolution Logic.
        Returns a dict describing the 'Plan'.
        """
        log(f"Resolving: Verb={verb}, Type={item_type}, Payload={payload}, Intent={intent}, Caller={caller}")

        plan = {
            "strategy": "stack_push",
            "role": "local",
            "cmd": None,
            "name": None,
            "payload": payload
        }

        # 1. Upgrade Intent if Caller is Menu
        if caller == "menu" and intent == "swap":
            intent = "replace"
            log("Upgraded swap to replace for menu caller")

        # 2. Handle ROLE Resolution
        if item_type == "ROLE":
            role_id = payload.lower()
            plan["role"] = role_id
            plan["name"] = role_id
            plan["cmd"] = resolve_role(role_id)
            
            # Smart Resolve: If this role is already active in 'local', switch to it
            local_state = self.get_stack_state("local")
            for idx, tab in enumerate(local_state.get("tabs", [])):
                if tab.get("name") == role_id:
                    plan["strategy"] = "stack_switch"
                    plan["index"] = idx
                    return plan
            
            plan["strategy"] = "stack_replace" if intent == "replace" else "stack_push"
            return plan

        # 3. Handle Structural Types (PLACE, PROJECT)
        if item_type in ["PLACE", "PROJECT"]:
            # If we are in a terminal role and have a TERM_PANE in tmux, we might want to send keys
            # For now, stick to stack-pushed zsh for isolation unless intentional 'remote' control sought
            plan["strategy"] = "stack_replace" if intent == "replace" else "stack_push"
            plan["cmd"] = f"cd {payload} && exec zsh -i"
            plan["name"] = Path(payload).name
            return plan

        # 4. Handle Content Types (NOTE, DOC)
        if item_type in ["NOTE", "DOC"]:
            # Check if editor is already open (Phase 3: Control Bridge)
            if self.bridge.get_nvim_pipe():
                plan["strategy"] = "remote_control"
                plan["target"] = "editor"
                plan["cmd"] = f":tabedit {payload}"
                plan["name"] = Path(payload).name
                return plan

            editor_cmd = os.environ.get("NEXUS_EDITOR", "nvim")
            plan["cmd"] = f"{editor_cmd} {payload}"
            plan["name"] = Path(payload).name
            plan["role"] = "editor"
            plan["strategy"] = "stack_push"
            return plan

        # 5. Handle AI Types (MODEL, AGENT)
        if item_type in ["MODEL", "AGENT"]:
            plan["cmd"] = f"{self.nexus_home}/modules/agents/bin/px-agent chat {payload}"
            plan["name"] = f"Chat: {payload}"
            plan["role"] = "chat"
            return plan

        # 6. Handle Direct ACTIONS
        if item_type == "ACTION":
            # Special internal actions
            if payload.startswith(":workspace"):
                plan["cmd"] = f"{self.nexus_home}/core/commands/workspace.sh {payload[10:].strip()}"
                plan["strategy"] = "exec_local"
            elif payload.startswith(":profile"):
                plan["cmd"] = f"{self.nexus_home}/core/commands/profile.sh load {payload[9:].strip()}"
                plan["strategy"] = "exec_local"
            elif payload.startswith(":focus"):
                plan["cmd"] = f"{self.nexus_home}/core/commands/focus.sh"
                plan["strategy"] = "exec_local"
            elif payload.startswith(":debug"):
                plan["cmd"] = f"{self.nexus_home}/core/exec/dap_handler.sh {payload[7:].strip()}"
                plan["strategy"] = "exec_local"
            else:
                plan["cmd"] = payload
                plan["strategy"] = "stack_replace" if intent == "replace" else "stack_push"
            return plan

        # 7. Fallback: RAW or Unknown
        plan["cmd"] = f"echo {payload}"
        return plan

if __name__ == "__main__":
    # Flexible CLI: 
    # Option 1: verb type payload [intent] [caller]
    # Option 2: type|payload (router style)
    
    resolver = IntentResolver()
    
    if len(sys.argv) == 2 and "|" in sys.argv[1]:
        itype, payload = sys.argv[1].split("|", 1)
        plan = resolver.resolve("run", itype, payload)
    elif len(sys.argv) >= 4:
        verb, itype, payload = sys.argv[1:4]
        intent = sys.argv[4] if len(sys.argv) > 4 else "push"
        caller = sys.argv[5] if len(sys.argv) > 5 else "terminal"
        plan = resolver.resolve(verb, itype, payload, intent, caller)
    else:
        print(json.dumps({"error": "Invalid arguments"}))
        sys.exit(1)

    print(json.dumps(plan))
