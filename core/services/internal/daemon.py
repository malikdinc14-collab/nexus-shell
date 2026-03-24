#!/usr/bin/env python3
# core/services/internal/nxs_d.py
import os
import sys
import json
import socket
import threading
import subprocess
import time
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

        # ── Negative Space: Assert both panes exist before swap ──
        all_panes = self.run_tmux(["list-panes", "-a", "-F", "#{pane_id}"], self.socket_label)
        pane_list = all_panes.split("\n") if all_panes else []

        if source not in pane_list:
            err = (f"[INVARIANT] ghost_swap source pane '{source}' does not exist in tmux. "
                   f"Target: '{target}'. Live panes: {pane_list}. "
                   f"Socket: {self.socket_label}")
            print(f"[{datetime.now()}] [TmuxAdapter] {err}", file=sys.stderr)
            return False

        if target not in pane_list:
            err = (f"[INVARIANT] ghost_swap target pane '{target}' does not exist in tmux. "
                   f"Source: '{source}'. Live panes: {pane_list}. "
                   f"Socket: {self.socket_label}")
            print(f"[{datetime.now()}] [TmuxAdapter] {err}", file=sys.stderr)
            return False

        res = self.run_tmux(["swap-pane", "-d", "-s", source, "-t", target], self.socket_label)
        if res is None:
            err = (f"[INVARIANT] swap-pane command failed despite both panes existing. "
                   f"Source: '{source}', Target: '{target}'. "
                   f"Possible: panes in different sessions or source=target window")
            print(f"[{datetime.now()}] [TmuxAdapter] {err}", file=sys.stderr)
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
        self.core = self._init_core()
        self._ensure_sub_services()

    def _init_core(self):
        """Initialize NexusCore with TmuxSurface backed by the daemon's tmux runner.

        Hydrates NexusCore's StackManager from existing daemon state so that
        stack operations route through NexusCore with full context.
        """
        try:
            from engine.surfaces.tmux_surface import TmuxSurface
            from engine.core import NexusCore

            socket_label = os.environ.get("SOCKET_LABEL")
            surface = TmuxSurface(run_tmux=self.run_tmux, socket_label=socket_label)
            core = NexusCore(
                surface=surface,
                workspace_dir=os.environ.get("PROJECT_ROOT", ""),
            )

            # Hydrate StackManager from existing daemon state
            stacks_data = self.state.get("stacks", {})
            if stacks_data:
                core.stacks.deserialize({"stacks": stacks_data})
                self.log(f"NexusCore hydrated with {len(stacks_data)} stacks")

            self.log("NexusCore initialized with TmuxSurface")
            return core
        except Exception as e:
            self.log(f"NexusCore init failed (non-fatal): {e}")
            return None

    def _resolve_adapter(self):
        if os.environ.get("NEXUS_SIMULATION") == "1":
            return MockTmuxAdapter()
        # Check for TMUX env, or if SOCKET_LABEL is set (daemon may be started
        # outside tmux but still need to control it via socket label)
        socket_label = os.environ.get("SOCKET_LABEL")
        if os.environ.get("TMUX") or socket_label:
            return TmuxAdapter(self.run_tmux, socket_label)
        # Fallback: check if any nexus tmux server is running
        try:
            import glob
            sockets = glob.glob("/tmp/tmux-*/nexus_*")
            if sockets:
                label = Path(sockets[0]).name
                return TmuxAdapter(self.run_tmux, label)
        except Exception:
            pass
        return WindowAdapter()

    def _ensure_sub_services(self):
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

    # --- Stack Registry ---

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

        if not self.core:
            return {"status": "error", "message": "NexusCore not initialized"}

        payload["identity"] = identity
        result = self.core.handle_stack_op(action, payload)
        if result.get("status") == "ok":
            self.state["stacks"] = self.core.stacks.serialize()["stacks"]
            self._save_state()
        return result

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
        
        orch = WorkspaceOrchestrator(NEXUS_HOME, Path(project_root), socket_label, core=self.core)
        orch.apply_composition(layout_name, target_window)
        return {"status": "ok"}

    def _handle_menu_open(self, payload):
        """Route menu open through NexusCore or fall back to direct handler."""
        try:
            from engine.api.menu_handler import handle_open
            result = handle_open()
            return {"status": "ok", "data": result}
        except Exception as e:
            self.log(f"menu_open error: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_menu_select(self, payload):
        """Route menu select through NexusCore — resolve AND dispatch."""
        node_id = payload.get("node_id")
        mode = payload.get("mode", "new_tab")
        if not node_id:
            return {"status": "error", "message": "No node_id provided"}

        if self.core:
            # Full path: NexusCore resolves cascade and dispatches through Surface
            result = self.core.select_and_dispatch(node_id, mode=mode)
            return result
        else:
            # Fallback: resolve node, dispatch via run_tmux directly
            self.log("[INVARIANT] NexusCore not available for menu_select — using fallback")
            try:
                from engine.api.menu_handler import handle_select
                result = handle_select(node_id, mode=mode)
                if result.get("action") == "exec" and result.get("command"):
                    self.run_tmux(["send-keys", result["command"], "Enter"])
                    return {"status": "ok", "action": "dispatched", "command": result["command"]}
                return result
            except Exception as e:
                self.log(f"menu_select fallback error: {e}")
                return {"status": "error", "message": str(e)}

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
                with self.lock:
                    # Sync NexusCore stack state into daemon state before returning
                    if self.core:
                        self.state["stacks"] = self.core.stacks.serialize()["stacks"]
                    response["data"] = self.state
            elif action == "set_state":
                with self.lock:
                    self.state = payload
                    self._save_state()
                    # Hydrate NexusCore if available
                    if self.core and "stacks" in payload:
                        self.core.stacks.deserialize({"stacks": payload.get("stacks", {})})
            elif action == "tmux": 
                # run_tmux handles its own adapter/mock logic, which might need the lock if mutating mock state
                response["data"] = self.run_tmux(payload.get("args", []), payload.get("socket_label"))
            elif action == "boot_layout": 
                # CRITICAL: No lock here.
                response = self._op_boot_layout(payload)
            elif action == "menu_open":
                response = self._handle_menu_open(payload)
            elif action == "menu_select":
                response = self._handle_menu_select(payload)
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
