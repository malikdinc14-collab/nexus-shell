#!/usr/bin/env python3
# core/services/internal/nxs_d.py
import os
import sys
import json
import socket
import threading
import subprocess
import time
import uuid
import getpass
from pathlib import Path
from queue import Queue
from datetime import datetime
from abc import ABC, abstractmethod

# Pillar Path Discovery
NEXUS_HOME = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[3]))
# Add core to sys.path for engine imports
sys.path.append(str(NEXUS_HOME))
sys.path.append(str(NEXUS_HOME / "core"))

try:
    from state_engine import NexusStateEngine
except ImportError:
    NexusStateEngine = None

USER = getpass.getuser()
DEFAULT_SOCKET = Path(f"/tmp/nexus_{USER}.sock")
SOCKET_PATH = Path(os.environ.get("NEXUS_SOCKET", DEFAULT_SOCKET))
RESERVOIR = "RESERVOIR"

class BaseContainerAdapter(ABC):
    @abstractmethod
    def get_focused_id(self): pass
    @abstractmethod
    def swap_containers(self, source, target): pass
    @abstractmethod
    def select_container(self, target): pass
    @abstractmethod
    def container_exists(self, target): pass
    @abstractmethod
    def set_metadata(self, target, key, value): pass
    @abstractmethod
    def get_metadata(self, target, key): pass
    @abstractmethod
    def get_geometry(self, target): pass
    @abstractmethod
    def set_geometry(self, target, geometry): pass

class TmuxAdapter(BaseContainerAdapter):
    def __init__(self, run_tmux_func, socket_label=None):
        self.run_tmux = run_tmux_func
        self.socket_label = socket_label

    def get_focused_id(self):
        return self.run_tmux(["display-message", "-p", "#{pane_id}"], self.socket_label)

    def swap_containers(self, source, target):
        if source == target: return True
        res = self.run_tmux(["swap-pane", "-d", "-s", source, "-t", target], self.socket_label)
        if res is None:
            self.run_tmux(["display-message", f"GhostSwap Error: swap-pane failed for {source} -> {target}"], self.socket_label)
            return False
        return True

    def select_container(self, target):
        return self.run_tmux(["select-pane", "-t", target], self.socket_label) is not None

    def container_exists(self, target):
        if not target or target == "null": return False
        exists = self.run_tmux(["list-panes", "-a", "-F", "#{pane_id}"], self.socket_label)
        return target in (exists.split("\n") if exists else [])

    def set_metadata(self, target, key, value):
        return self.run_tmux(["set-option", "-p", "-t", target, key, str(value)], self.socket_label) is not None

    def get_metadata(self, target, key):
        val = self.run_tmux(["display-message", "-p", "-t", target, f"#{{{key}}}"], self.socket_label)
        return val if val != "null" else None

    def get_geometry(self, target):
        # Axiom: Record absolute coordinates and proportions
        res = self.run_tmux(["display-message", "-p", "-t", target, "#{pane_left},#{pane_top},#{pane_width},#{pane_height}"], self.socket_label)
        if not res or res == "null": return None
        parts = res.split(",")
        return {
            "x": int(parts[0]), "y": int(parts[1]),
            "w": int(parts[2]), "h": int(parts[3])
        }

    def set_geometry(self, target, geo):
        # For now, we use resize-pane. Future: select-layout for complex restorations.
        self.run_tmux(["resize-pane", "-t", target, "-x", str(geo["w"]), "-y", str(geo["h"])], self.socket_label)

class MockTmuxAdapter(BaseContainerAdapter):
    """
    A high-fidelity in-memory mock of the Tmux interaction layer.
    Used for logic-based simulations and testing environments where
    the real tmux binary is unavailable or restricted.
    """
    def __init__(self):
        self.panes = {} # pid -> {metadata: {}, geo: {}}
        self.focused_pane = None
        self.next_pane_idx = 0

    def _create_pane(self, pid=None):
        if pid is None:
            pid = f"%{self.next_pane_idx}"
            self.next_pane_idx += 1
        if pid not in self.panes:
            self.panes[pid] = {"metadata": {}, "geo": {"x": 0, "y": 0, "w": 80, "h": 24}}
        return pid

    def get_focused_id(self):
        return self.focused_pane

    def swap_containers(self, source, target):
        return True

    def select_container(self, target):
        if target in self.panes:
            self.focused_pane = target
            return True
        return False

    def container_exists(self, target):
        return target in self.panes

    def set_metadata(self, target, key, value):
        pid = self._create_pane(target)
        # Handle tmux display-message format (strip #{...})
        clean_key = key.replace("#{", "").replace("}", "")
        self.panes[pid]["metadata"][clean_key] = str(value)
        return True

    def get_metadata(self, target, key):
        if target not in self.panes: return None
        clean_key = key.replace("#{", "").replace("}", "")
        return self.panes[target]["metadata"].get(clean_key)

    def get_geometry(self, target):
        if target not in self.panes: return None
        return self.panes[target]["geo"]

    def set_geometry(self, target, geo):
        if target in self.panes:
            self.panes[target]["geo"] = geo

class WindowAdapter(BaseContainerAdapter):
    def get_focused_id(self): return None
    def swap_containers(self, source, target): return False
    def select_container(self, target): return False
    def container_exists(self, target): return False
    def set_metadata(self, target, key, value): return False
    def get_metadata(self, target, key): return None
    def get_geometry(self, target): return None
    def set_geometry(self, target, geo): pass

class NexusDaemon:
    def __init__(self):
        self.state_engine = NexusStateEngine(os.environ.get("PROJECT_ROOT")) if NexusStateEngine else None
        self.state = self._load_initial_state()
        self.registry = self.state["stacks"] # Primary pointer for ops
        self.running = True
        self.lock = threading.Lock()
        self.log_file = Path(f"/tmp/nexus_{USER}/daemon.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.adapter = self._resolve_adapter()
        self._ensure_sub_services()

    def _resolve_adapter(self):
        if os.environ.get("NEXUS_SIMULATION") == "1":
            return MockTmuxAdapter()
        if os.environ.get("TMUX"):
            return TmuxAdapter(self.run_tmux, os.environ.get("SOCKET_LABEL"))
        return WindowAdapter()

    def _ensure_sub_services(self):
        bus_py = NEXUS_HOME / "core/engine/bus/event_server.py"
        bus_log = f"/tmp/nexus_{USER}/bus_global.log"
        if bus_py.exists():
            self.log("Starting Event Bus...")
            subprocess.Popen([sys.executable, str(bus_py)], stdout=open(bus_log, "a"), stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)

        sid_py = NEXUS_HOME / "core/engine/ai/sid.py"
        sid_log = f"/tmp/nexus_{USER}/sid_global.log"
        if sid_py.exists():
            self.log("Starting SID...")
            subprocess.Popen([sys.executable, str(sid_py)], stdout=open(sid_log, "a"), stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)

    def _load_initial_state(self):
        if self.state_engine:
            data = self.state_engine.get("ui.stacks") or {}
            if "stacks" not in data: return {"stacks": {}}
            return data
        return {"stacks": {}}

    def _save_state(self):
        if self.state_engine:
            self.state_engine.set("ui.stacks", self.state)

    def log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [nxs-d] {msg}"
        print(line, flush=True)
        with open(self.log_file, "a") as f: f.write(line + "\n")

    def run_tmux(self, args, socket_label=None):
        # 1. Resolve effective socket identification
        sl = socket_label or os.environ.get("NEXUS_SOCKET") or os.environ.get("SOCKET_LABEL")
        
        # 2. Construct command (Path vs Label)
        cmd = ["tmux"]
        if sl:
            if sl.startswith("/"):
                cmd += ["-S", sl]
            else:
                cmd += ["-L", sl]
        full_cmd = cmd + args
        
        # 3. Log for Full Observability (Axiom-O)
        self.log(f"TX: {' '.join(full_cmd)}")
        
        try:
            process = subprocess.run(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            # Decode with replacement to handle potential binary noise/escapes
            res = process.stdout.decode("utf-8", errors="replace").strip()
            self.log(f"RX Success: {res[:100]}{'...' if len(res)>100 else ''}")
            return res
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode("utf-8", errors="replace").strip()
            self.log(f"RX Error: {err}")
            return None
        except Exception as e:
            self.log(f"RX Fatal: {e}")
            return None

    def ghost_swap(self, source, target):
        if source == target: return True
        return self.adapter.swap_containers(source, target)

    # --- Stack Registry Logic ---

    def _get_stack_by_identity(self, identity):
        registry = self.state.get("stacks", {})
        if identity in registry: return identity, registry[identity]
        for sid, stack in registry.items():
            if stack.get("role") == identity: return sid, stack
            if identity in stack.get("tags", []): return sid, stack
        return None, None

    def _get_or_create_stack(self, identity, initial_pane=None):
        # AXIOM: Prioritize Local Context (off-by-default Global Role Singletons)
        # If the initial pane already has a stack ID, that is our authoritative target.
        if initial_pane:
            pane_sid = self.adapter.get_metadata(initial_pane, "@nexus_stack_id")
            if pane_sid and pane_sid in self.state["stacks"]:
                return pane_sid, self.state["stacks"][pane_sid]

        # Explicit UUID resolution
        if identity and identity.startswith("stack_"):
            if identity in self.state["stacks"]:
                return identity, self.state["stacks"][identity]
        
        # Identity-Resolution (Role Lookup)
        # Fallback to finding an existing stack by its Role if the pane itself lacked explicit metadata.
        if identity and not identity.startswith("stack_"):
            sid, stack = self._get_stack_by_identity(identity)
            if sid: return sid, stack
        
        # New Stack: Resolve SID vs Role
        is_uuid = identity and identity.startswith("stack_")
        sid = identity if is_uuid else f"stack_{uuid.uuid4().hex[:6]}"
        role = None if is_uuid else identity
        
        new_stack = {
            "role": role, 
            "tags": [], 
            "active_index": 0, 
            "tabs": [],
            "metadata": {}
        }
        if initial_pane: 
            new_stack["tabs"].append({
                "id": initial_pane, 
                "name": role.capitalize() if role else "Shell", 
                "status": "VISIBLE"
            })
        
        self.state["stacks"][sid] = new_stack
        self._save_state()
        return sid, new_stack

    def _scrub_registry(self):
        registry = self.state.get("stacks", {})
        dead_stacks = []
        for sid, stack in registry.items():
            tabs = stack.get("tabs", [])
            valid_tabs = [t for t in tabs if self.adapter.container_exists(t["id"])]
            if len(valid_tabs) != len(tabs):
                if not valid_tabs: dead_stacks.append(sid)
                else:
                    stack["tabs"] = valid_tabs
                    stack["active_index"] = min(stack["active_index"], len(valid_tabs)-1)
        for sid in dead_stacks: del self.state["stacks"][sid]
        if dead_stacks: self._save_state()

    def handle_stack_op(self, action, payload):
        identity = payload.get("role") or payload.get("stack_id")
        if not identity: return {"status": "error", "message": "No identity provided"}
        self.log(f"Stack Op: {action} for {identity}")
        self._scrub_registry()
        ops = {
            "push": self._op_push, 
            "switch": self._op_switch, 
            "replace": self._op_replace, 
            "close": self._op_close,
            "tag": self._op_tag,
            "untag": self._op_untag,
            "rename": self._op_rename,
            "adopt": self._op_adopt
        }
        if action in ops: return ops[action](identity, payload)
        return {"status": "error", "message": f"Unknown op: {action}"}

    def _op_tag(self, identity, payload):
        tag = payload.get("tag")
        if not tag: return {"status": "error", "message": "No tag provided"}
        sid, stack = self._get_stack_by_identity(identity)
        if not stack: return {"status": "error", "message": "Stack not found"}
        if tag not in stack["tags"]:
            stack["tags"].append(tag)
            self._save_state()
        return {"status": "ok"}

    def _op_untag(self, identity, payload):
        tag = payload.get("tag")
        sid, stack = self._get_stack_by_identity(identity)
        if not stack: return {"status": "error", "message": "Stack not found"}
        if tag in stack["tags"]:
            stack["tags"].remove(tag)
            self._save_state()
        return {"status": "ok"}

    def _op_rename(self, identity, payload):
        name = payload.get("name")
        if not name: return {"status": "error", "message": "No name provided"}
        sid, stack = self._get_stack_by_identity(identity)
        if not stack: return {"status": "error", "message": "Stack not found"}
        stack["role"] = name # Promoting a role name is effectively renaming the stack's primary alias
        self._save_state()
        return {"status": "ok"}

    def _get_visible_container(self, stack, focused_id):
        tabs = stack.get("tabs", [])
        if any(t["id"] == focused_id for t in tabs): return focused_id
        for tab in tabs:
            if tab.get("status") == "VISIBLE": return tab["id"]
        for tab in tabs:
            win_name = self.adapter.get_metadata(tab["id"], "window_name")
            if win_name and win_name != RESERVOIR: return tab["id"]
        return tabs[stack["active_index"]]["id"] if tabs else None

    def _op_push(self, identity, payload):
        new_id = payload.get("pane_id")
        name = payload.get("name", "Shell")
        focused_id = self.adapter.get_focused_id()
        sid, stack = self._get_or_create_stack(identity, initial_pane=focused_id)
        if not identity.startswith("stack_") and not stack.get("role"):
            stack["role"] = identity
            self.adapter.set_metadata(focused_id, "@nexus_role", identity)
        
        visible_id = self._get_visible_container(stack, focused_id)
        # Record geometry of the currently visible pane before it goes to background
        geo = self.adapter.get_geometry(visible_id)
        for t in stack["tabs"]:
            if t["id"] == visible_id:
                t["geometry"] = geo
                t["status"] = "BACKGROUND"
            else:
                t["status"] = "BACKGROUND"
        
        if self.ghost_swap(visible_id, new_id):
            self.adapter.select_container(new_id)
            stack["tabs"].append({"id": new_id, "name": name, "status": "VISIBLE", "geometry": geo})
            stack["active_index"] = len(stack["tabs"]) - 1
            self._save_state()
            return {"status": "ok", "stack_id": sid}
        return {"status": "error", "message": "Push failed"}

    def _op_adopt(self, identity, payload):
        """
        Adopts a pre-existing container into the stack registry.
        Used during boot or when a standalone tool is initialized.
        """
        pane_id = payload.get("pane_id")
        name = payload.get("name", "Shell")
        if not pane_id: return {"status": "error", "message": "No pane_id provided"}
        
        sid, stack = self._get_or_create_stack(identity, initial_pane=pane_id)
        # Ensure the pane is marked as VISIBLE if it's the current one
        for tab in stack["tabs"]:
            if tab["id"] == pane_id:
                tab["status"] = "VISIBLE"
                tab["name"] = name
        
        # Propagate metadata back to the pane
        self.adapter.set_metadata(pane_id, "@nexus_stack_id", sid)
        if stack.get("role"):
            self.adapter.set_metadata(pane_id, "@nexus_role", stack["role"])
            
        self._save_state()
        return {"status": "ok", "stack_id": sid}

    def _op_boot_layout(self, payload):
        layout_name = payload.get("name")
        target_window = payload.get("window")
        if not layout_name: return {"status": "error", "message": "No layout name provided"}
        
        self.log(f"Booting layout: {layout_name} in {target_window}")
        
        # Late import to avoid circularities
        from engine.orchestration.workspace import WorkspaceOrchestrator
        
        # Prioritize parameters from payload, fall back to environment
        project_root = payload.get("project_root") or os.environ.get("PROJECT_ROOT", os.getcwd())
        socket_label = payload.get("socket_label") or os.environ.get("SOCKET_LABEL")
        
        # Ensure environment is consistent for sub-processes (like 'stack init')
        if socket_label: os.environ["SOCKET_LABEL"] = socket_label
        if project_root: os.environ["PROJECT_ROOT"] = str(project_root)
        
        orch = WorkspaceOrchestrator(NEXUS_HOME, Path(project_root), socket_label)
        orch.apply_composition(layout_name, target_window)
        return {"status": "ok"}

    def _op_switch(self, identity, payload):
        try: index = int(payload.get("index", 0))
        except: return {"status": "error", "message": "Invalid index"}
        sid, stack = self._get_stack_by_identity(identity)
        if not stack or index >= len(stack["tabs"]): return {"status": "error", "message": "Not found"}
        
        target_id = stack["tabs"][index]["id"]
        focused_id = self.adapter.get_focused_id()
        visible_id = self._get_visible_container(stack, focused_id)
        
        if visible_id != target_id:
            # Snapshot outgoing geometry
            outgoing_geo = self.adapter.get_geometry(visible_id)
            if self.ghost_swap(visible_id, target_id):
                self.adapter.select_container(target_id)
                # Restore incoming geometry if available
                incoming_geo = stack["tabs"][index].get("geometry")
                if incoming_geo:
                    self.adapter.set_geometry(target_id, incoming_geo)
                
                for i, t in enumerate(stack["tabs"]):
                    if t["id"] == visible_id: t["geometry"] = outgoing_geo
                    t["status"] = "VISIBLE" if i == index else "BACKGROUND"
                
                stack["active_index"] = index
                self._save_state()
                return {"status": "ok"}
            return {"status": "error", "message": "Switch failed"}
        return {"status": "ok", "message": "Already active"}

    def _op_replace(self, identity, payload):
        new_id = payload.get("pane_id")
        name = payload.get("name", "Shell")
        sid, stack = self._get_stack_by_identity(identity)
        if not stack: return self._op_push(identity, payload)
        
        idx = stack["active_index"]
        target_to_replace = stack["tabs"][idx]["id"]
        visible_id = self._get_visible_container(stack, self.adapter.get_focused_id())
        
        # Capture current geometry
        geo = self.adapter.get_geometry(visible_id)
        
        if self.ghost_swap(visible_id, new_id):
            self.adapter.select_container(new_id)
            # Apply geometry to new pane
            if geo: self.adapter.set_geometry(new_id, geo)
            
            if target_to_replace != new_id:
                self.run_tmux(["kill-pane", "-t", target_to_replace], getattr(self.adapter, 'socket_label', None))
            stack["tabs"][idx] = {"id": new_id, "name": name, "status": "VISIBLE", "geometry": geo}
            self._save_state()
            return {"status": "ok"}
        return {"status": "error", "message": "Replace failed"}

    def _op_close(self, identity):
        sid, stack = self._get_stack_by_identity(identity)
        if not stack or not stack["tabs"]: return {"status": "error", "message": "Empty"}
        idx = stack["active_index"]
        if idx == 0: return {"status": "error", "message": "Foundation protected"}
        target_id = stack["tabs"][idx]["id"]
        visible_id = self._get_visible_container(stack, self.adapter.get_focused_id())
        foundation_id = stack["tabs"][0]["id"]
        if self.ghost_swap(visible_id, foundation_id):
            self.adapter.select_container(foundation_id)
            self.run_tmux(["kill-pane", "-t", target_id], getattr(self.adapter, 'socket_label', None))
            stack["tabs"].pop(idx)
            stack["active_index"] = 0
            for i, t in enumerate(stack["tabs"]): t["status"] = "VISIBLE" if i == 0 else "BACKGROUND"
            self._save_state()
            return {"status": "ok"}
        return {"status": "error", "message": "Close failed"}

    def handle_client(self, conn):
        try:
            data = conn.recv(8192)
            if not data: return
            msg = json.loads(data.decode())
            action = msg.get("action")
            payload = msg.get("payload", {})
            response = {"status": "ok"}
            # Granular Locking: Only lock for state-mutating or state-reading operations.
            # Long-running operations like boot_layout MUST NOT hold the global lock to avoid deadlocks
            # when the orchestrator makes recursive calls back to the daemon.
            if action == "ping": 
                response["data"] = "pong"
            elif action == "get_state": 
                with self.lock: response["data"] = self.state
            elif action == "set_state": 
                with self.lock: self.state = payload; self._save_state()
            elif action == "tmux": 
                # run_tmux handles its own adapter/mock logic, which might need the lock if mutating mock state
                response["data"] = self.run_tmux(payload.get("args", []), payload.get("socket_label"))
            elif action == "boot_layout": 
                # CRITICAL: No lock here.
                response = self._op_boot_layout(payload)
            elif action.startswith("stack_"): 
                with self.lock: response = self.handle_stack_op(action.replace("stack_", ""), payload)
            else: 
                response["status"] = "error"; response["message"] = f"Unknown action: {action}"
            
            conn.sendall(json.dumps(response).encode())
        except Exception as e:
            self.log(f"Handler Error: {e}")
            try: conn.sendall(json.dumps({"status": "error", "message": str(e)}).encode())
            except: pass
        finally: conn.close()

    def start(self):
        if SOCKET_PATH.exists(): SOCKET_PATH.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(SOCKET_PATH))
        server.listen(10)
        self.log(f"Nexus Daemon listening on {SOCKET_PATH}")
        try:
            while self.running:
                conn, _ = server.accept()
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
        finally:
            self.running = False
            if SOCKET_PATH.exists(): SOCKET_PATH.unlink()

if __name__ == "__main__":
    daemon = NexusDaemon()
    daemon.start()
